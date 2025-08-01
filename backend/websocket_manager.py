import json
import os
import asyncio
from fastapi import APIRouter, WebSocket
from typing import List

# Connected WebSocket clients
connected_clients: List[WebSocket] = []

# Screenshot directory path
SCREENSHOT_DIR = "screenshots"

# WebSocket router
websocket_router = APIRouter()

def find_latest_screenshot(pc_id: str):
    """Finds the most recent screenshot for a given PC."""
    pc_folder = os.path.join(SCREENSHOT_DIR, pc_id)
    
    if not os.path.exists(pc_folder):
        return None  # No screenshots folder exists for this PC
    
    # Get all files in the PC-specific folder
    files = [f for f in os.listdir(pc_folder) if f.startswith(pc_id)]
    
    # Sort files by timestamp (newest first)
    files.sort(reverse=True)
    
    if files:
        return f"/screenshots/{pc_id}/{files[0]}"  # Return latest screenshot URL with correct path
    return None  # No screenshot available

async def notify_clients(logs):
    """Send new logs to all connected WebSocket clients, including screenshot URLs."""
    if not connected_clients:
        return  # No clients connected

    # Convert logs to JSON serializable format
    logs_dict = []
    for log in logs:
        logs_dict.append({
            "pc_id": log.pc_id,
            "active_window": log.active_window,
            "active_process": log.active_process,
            "status": log.status,
            "timestamp": log.timestamp.isoformat(),  # Convert datetime to string
            "screenshot_url": find_latest_screenshot(log.pc_id)  # Get Screenshot URL
        })

    # Send JSON data to all clients
    message = json.dumps({"logs": logs_dict})
    await asyncio.gather(*(client.send_text(message) for client in connected_clients))

async def notify_specific_pc(pc_id: str):
    """Sends a WebSocket command to a specific PC to take a screenshot."""
    message = json.dumps({"action": "capture_screenshot", "pc_id": pc_id})
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass  # Ignore disconnected clients

@websocket_router.websocket("/ws")
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