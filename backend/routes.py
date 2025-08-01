import os
from fastapi import APIRouter, BackgroundTasks, Query, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime

from models import LogRequest, ActivityLog, LogResponse, ScreenshotResponse
from database import insert_logs, fetch_logs
from websocket_manager import notify_clients, notify_specific_pc
from analysis import analyze_pc_activity, analyze_window_usage_per_day

router = APIRouter()

# Screenshot directory
SCREENSHOT_DIR = "screenshots"

@router.post("/log_activity/", response_model=LogResponse)
async def log_activity(request: LogRequest, background_tasks: BackgroundTasks):
    """Batch insert logs asynchronously."""
    if not request.logs:
        raise HTTPException(status_code=400, detail="No logs provided.")
    
    background_tasks.add_task(insert_logs, request.logs, notify_clients)
    return {"message": f"{len(request.logs)} logs queued for insertion"}

@router.get("/get_logs/")
async def get_logs(
    pc_id: Optional[str] = Query(None, description="Filter by PC ID"),
    start_time: Optional[str] = Query(None, description="Start timestamp (YYYY-MM-DD HH:MM:SS)"),
    end_time: Optional[str] = Query(None, description="End timestamp (YYYY-MM-DD HH:MM:SS)")
):
    """Retrieve logs with optional filtering."""
    # Parse datetime strings if provided
    start_datetime = None
    end_datetime = None
    
    if start_time:
        try:
            start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format. Use YYYY-MM-DD HH:MM:SS")
    
    if end_time:
        try:
            end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format. Use YYYY-MM-DD HH:MM:SS")

    logs = fetch_logs(pc_id, start_datetime, end_datetime)
    
    if not logs:
        return {"message": "No logs found."}

    return {"logs": logs}

@router.post("/upload_screenshot/", response_model=ScreenshotResponse)
async def upload_screenshot(pc_id: str = Form(...), screenshot: UploadFile = File(...)):
    """Receives and stores a screenshot, returns the full URL."""
    try:
        #create ng folder
        pc_folder = os.path.join(SCREENSHOT_DIR, pc_id)
        os.makedirs(pc_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{pc_id}_{timestamp}.png"
        file_path = os.path.join(pc_folder, filename)

        # Save the screenshot
        with open(file_path, "wb") as buffer:
            buffer.write(await screenshot.read())

        # Full URL to access the screenshot
        screenshot_url = f"http://localhost/new/Client-Server-Monitoring-System/backend/screenshots/{pc_id}/{filename}"
        print(f"📸 Screenshot saved: {screenshot_url}")

        return {"message": "Screenshot uploaded", "screenshot_url": screenshot_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    

@router.get("/api/activity-report/{pc_id}")
def get_activity_report(pc_id: str):
    logs = fetch_logs(pc_id=pc_id)
    result = analyze_pc_activity(logs)
    return JSONResponse(content=result)

@router.get("/api/window-usage/{pc_id}")
def get_window_usage(pc_id: str):
    logs = fetch_logs(pc_id=pc_id)
    usage_report = analyze_window_usage_per_day(logs)
    return JSONResponse(content=usage_report)
