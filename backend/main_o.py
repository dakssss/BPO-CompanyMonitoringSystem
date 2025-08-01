import os
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException, WebSocket, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import mysql.connector
from mysql.connector import pooling
import asyncio  
import json
app = FastAPI()

# ✅ Connection Pool (Handles Up to 20 Concurrent Requests)
db_pool = pooling.MySQLConnectionPool(
    pool_name="monitoring_pool",
    pool_size=20,  
    host="localhost",
    user="root",
    password="",
    database="monitoring_system"
)

# ✅ Define Pydantic Models
class ActivityLog(BaseModel):
    pc_id: str
    active_window: str
    active_process: str
    status: str
    timestamp: datetime  # Ensures proper datetime parsing

class LogRequest(BaseModel):
    logs: List[ActivityLog]

# ✅ Background Task Handler (Batch Insert Logs)


SCREENSHOT_DIR = "C:/xampp/htdocs/Monitoring System/backend/screenshots"  # Adjust path as needed

async def notify_clients(logs: List[ActivityLog]):
    """Send new logs to all connected WebSocket clients, including screenshot URLs."""
    if not connected_clients:
        return  # No clients connected

    # ✅ Convert logs to JSON serializable format
    logs_dict = []
    for log in logs:
        logs_dict.append({
            "pc_id": log.pc_id,
            "active_window": log.active_window,
            "active_process": log.active_process,
            "status": log.status,
            "timestamp": log.timestamp.isoformat(),  # ✅ Convert datetime to string
            "screenshot_url": find_latest_screenshot(log.pc_id)  # ✅ Get Screenshot URL
        })

    # ✅ Send JSON data to all clients
    message = json.dumps({"logs": logs_dict})
    await asyncio.gather(*(client.send_text(message) for client in connected_clients))

def find_latest_screenshot(pc_id: str):
    """Finds the most recent screenshot for a given PC."""
    if not os.path.exists(SCREENSHOT_DIR):
        return None  # No screenshots folder exists

    files = sorted(
        [f for f in os.listdir(SCREENSHOT_DIR) if f.startswith(pc_id)],
        reverse=True
    )

    if files:
        return f"/screenshots/{files[0]}"  # ✅ Return latest screenshot URL
    return None  # No screenshot available

def insert_logs(logs: List[ActivityLog]):
    """Inserts logs into the database and notifies WebSocket clients."""
    conn = db_pool.get_connection()
    cursor = conn.cursor()

    try:
        sql = """
        INSERT INTO activity_logs (pc_id, active_window, active_process, status, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = [(log.pc_id, log.active_window, log.active_process, log.status, log.timestamp) for log in logs]

        cursor.executemany(sql, values)  
        conn.commit()
        print(f"✅ {len(logs)} logs inserted successfully.")

        # ✅ Run WebSocket notification safely in a separate thread
        try:
            asyncio.run(notify_clients(logs))
        except RuntimeError:
            print("❌ Async function was called in an existing event loop.")

    except Exception as e:
        conn.rollback()
        print(f"❌ DB Error: {e}")

    finally:
        cursor.close()
        conn.close()






# ✅ Log Activity Endpoint (Async)
@app.post("/log_activity/")
async def log_activity(request: LogRequest, background_tasks: BackgroundTasks):
    """Batch insert logs asynchronously."""
    if not request.logs:
        raise HTTPException(status_code=400, detail="No logs provided.")
    
    background_tasks.add_task(insert_logs, request.logs)
    return {"message": f"{len(request.logs)} logs queued for insertion"}

# ✅ Get Logs with Filters
@app.get("/get_logs/")
async def get_logs(
    pc_id: Optional[str] = Query(None, description="Filter by PC ID"),
    start_time: Optional[str] = Query(None, description="Start timestamp (YYYY-MM-DD HH:MM:SS)"),
    end_time: Optional[str] = Query(None, description="End timestamp (YYYY-MM-DD HH:MM:SS)")
):
    """Retrieve logs with optional filtering."""
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM activity_logs WHERE 1=1"
    values = []

    if pc_id:
        query += " AND pc_id = %s"
        values.append(pc_id)
    
    if start_time:
        try:
            start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            query += " AND timestamp >= %s"
            values.append(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format. Use YYYY-MM-DD HH:MM:SS")
    
    if end_time:
        try:
            end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            query += " AND timestamp <= %s"
            values.append(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format. Use YYYY-MM-DD HH:MM:SS")

    cursor.execute(query, values)
    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    if not logs:
        return {"message": "No logs found."}

    return {"logs": logs}


# ✅ Store Connected WebSocket Clients
connected_clients: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for real-time communication."""
    await websocket.accept()
    connected_clients.append(websocket)
    print("✅ New WebSocket Client Connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("action") == "capture_screenshot":
                pc_id = message.get("pc_id")
                if pc_id:
                    await notify_specific_pc(pc_id)  # Forward the request

    except Exception as e:
        print(f"❌ WebSocket Error: {e}")
    finally:
        connected_clients.remove(websocket)
        print("❌ WebSocket Disconnected")


async def notify_specific_pc(pc_id: str):
    """Sends a WebSocket command to a specific PC to take a screenshot."""
    message = json.dumps({"action": "capture_screenshot", "pc_id": pc_id})
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass  # Ignore disconnected clients



# ✅ Ensure screenshot storage directory exists
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ✅ Serve screenshots as static files
app.mount("/screenshots", StaticFiles(directory=SCREENSHOT_DIR), name="screenshots")

# ✅ New Endpoint: Upload Screenshot
@app.post("/upload_screenshot/")
async def upload_screenshot(pc_id: str = Form(...), screenshot: UploadFile = File(...)):
    """Receives and stores a screenshot, returns the full URL."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pc_id}_{timestamp}.png"
        file_path = os.path.join(SCREENSHOT_DIR, filename)

        # ✅ Save the screenshot
        with open(file_path, "wb") as buffer:
            buffer.write(await screenshot.read())

        # ✅ Full URL to access the screenshot
        screenshot_url = f"http://localhost/Monitoring%20System/backend/screenshots/{filename}"
        print(f"📸 Screenshot saved: {screenshot_url}")

        return {"message": "Screenshot uploaded", "screenshot_url": screenshot_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
