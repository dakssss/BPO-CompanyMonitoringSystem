from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from database import init_db_pool
from routes import router
from websocket_manager import websocket_router
from webrtc_manager import webrtc_router

# Initialize app
app = FastAPI()

# Initialize database connection pool
init_db_pool()

# Define screenshot directory
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Mount static files for screenshots
app.mount("/screenshots", StaticFiles(directory=SCREENSHOT_DIR), name="screenshots")

# Include API routes
app.include_router(router)

# Include WebSocket routes
app.include_router(websocket_router)

# Include WebRTC routes
app.include_router(webrtc_router)

# Add CORS middleware to allow your frontend to communicate with FastAPI

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://172.16.1.5",  # <- if you're using VS Code Live Server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,
        #ssl_keyfile=r"C:\xampp\htdocs\Monitoring System\backend\msi.pem",
        #ssl_certfile=r"C:\xampp\htdocs\Monitoring System\backend\cert.crt"
    )