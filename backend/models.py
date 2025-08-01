from pydantic import BaseModel
from typing import List
from datetime import datetime

class ActivityLog(BaseModel):
    """Model for individual activity log entries."""
    pc_id: str
    active_window: str
    active_process: str
    status: str
    timestamp: datetime

class LogRequest(BaseModel):
    """Model for batch log request."""
    logs: List[ActivityLog]

class LogResponse(BaseModel):
    """Model for log response."""
    message: str

class ScreenshotResponse(BaseModel):
    """Model for screenshot upload response."""
    message: str
    screenshot_url: str