import time
import psutil
import pygetwindow as gw
import requests
import pyautogui
import websockets
import asyncio
from pynput import mouse, keyboard
from datetime import datetime
import socket
import json
import os
import cv2
import numpy as np
import base64
import threading

# ✅ Server URLs
API_URL = "http://172.16.1.5:8000/log_activity/"
SCREENSHOT_URL = "http://172.16.1.5:8000/upload_screenshot"
WS_URL = "ws://172.16.1.5:8000/ws"
WEBRTC_WS_URL = "ws://172.16.1.5:8000/webrtc"

# ✅ Constants
IDLE_THRESHOLD = 30  # seconds
PC_ID = socket.gethostname()
take_screenshot = "No"  # ✅ Screenshot request tracker
stream_screen = False   # ✅ Screen streaming tracker
STREAM_FPS = 5          # ✅ Frames per second for streaming

# ✅ Track last activity time
last_activity_time = time.time()

def on_activity(event):
    """Updates last activity time on user activity."""
    global last_activity_time
    last_activity_time = time.time()

# ✅ Mouse and Keyboard listeners
mouse_listener = mouse.Listener(on_move=on_activity, on_click=on_activity, on_scroll=on_activity)
keyboard_listener = keyboard.Listener(on_press=on_activity)
mouse_listener.start()
keyboard_listener.start()

def get_active_window():
    """Gets the title of the active window."""
    try:
        window = gw.getActiveWindow()
        return window.title if window else "Unknown"
    except:
        return "Unknown"

def get_active_process():
    """Gets the active process name."""
    try:
        window = gw.getActiveWindow()
        if window:
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                if proc.pid == window.pid:
                    return proc.info['name']
    except:
        pass
    return "Unknown"

import tempfile

def capture_screenshot(pc_id):
    """Takes a screenshot, saves it temporarily, uploads it, and resets the flag."""
    global take_screenshot  

    # ✅ Use a TEMPORARY directory (works on all PCs)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        screenshot_path = temp_file.name  # Get temp file path

    # ✅ Take Screenshot
    pyautogui.screenshot(screenshot_path)

    try:
        with open(screenshot_path, "rb") as file:
            response = requests.post(
                SCREENSHOT_URL,
                files={"screenshot": file},
                data={"pc_id": pc_id},
                verify=False
            )

        if response.status_code == 200:
            print(f"✅ Screenshot uploaded successfully: {screenshot_path}")
        else:
            print(f"❌ Screenshot upload failed: {response.text}")
    except Exception as e:
        print(f"❌ Error uploading screenshot: {e}")

    # ✅ Delete local temp file after upload
    os.remove(screenshot_path)

    # ✅ Reset screenshot request flag
    take_screenshot = "No"
    print("🔄 Screenshot flag reset to No")

def send_activity_log():
    """Sends activity data to the server immediately."""
    global take_screenshot

    active_window = get_active_window()
    active_process = get_active_process()
    idle_time = time.time() - last_activity_time
    status = "Idle" if idle_time > IDLE_THRESHOLD else "Active"
    timestamp = datetime.now().isoformat()

    data = {
        "logs": [{
            "pc_id": PC_ID,
            "active_window": active_window,
            "active_process": active_process,
            "status": status,
            "timestamp": timestamp,
            "take_screenshot": take_screenshot
        }]
    }

    # In send_activity_log()
    try:
        response = requests.post(API_URL, json=data, verify=False)
        print(f"✅ Sent: {data} | Response: {response.status_code} | Response Body: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending data: {e}")

async def handle_screenshot():
    """Handles immediate screenshot capture and log update."""
    global take_screenshot

    print("📸 Taking screenshot as requested by UI...")
    capture_screenshot(PC_ID)
    print("📸 Screenshot captured and uploaded.")

    # ✅ Send updated logs immediately after capturing the screenshot
    send_activity_log()

async def send_activity():
    """Sends activity data to the server every 5 seconds."""
    while True:
        send_activity_log()
        await asyncio.sleep(5)  # ✅ Regular interval

# ✅ WebRTC Screen Streaming Functions
async def stream_screen_feed(ws):
    """Streams screen content over WebSocket using a simplified WebRTC approach."""
    global stream_screen
    
    print("🎥 Starting screen streaming...")
    
    try:
        while stream_screen:
            # Capture screen
            screen = pyautogui.screenshot()
            frame = np.array(screen)
            # Convert to BGR (OpenCV format)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Resize to reduce bandwidth (adjust as needed)
            frame = cv2.resize(frame, (1280, 720))
            
            # Convert to JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            
            # Convert to base64 for transmission
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            # Send frame
            await ws.send(json.dumps({
                "type": "video-frame",
                "pc_id": PC_ID,
                "frame": jpg_as_text,
                "timestamp": datetime.now().isoformat()
            }))
            
            # Control frame rate
            await asyncio.sleep(1/STREAM_FPS)
    
    except Exception as e:
        print(f"❌ Streaming error: {e}")
    finally:
        print("🛑 Screen streaming stopped")
        stream_screen = False

async def webrtc_client():
    """Handles WebRTC WebSocket communication with the server."""
    global stream_screen
    
    while True:
        try:
            async with websockets.connect(WEBRTC_WS_URL) as ws:
                # Register this client
                await ws.send(json.dumps({
                    "type": "register",
                    "pc_id": PC_ID,
                    "client_type": "sender"
                }))
                
                # Wait for messages
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    if data.get("type") == "start-stream" and data.get("pc_id") == PC_ID:
                        stream_screen = True
                        asyncio.create_task(stream_screen_feed(ws))
                    
                    elif data.get("type") == "stop-stream" and data.get("pc_id") == PC_ID:
                        stream_screen = False
                        
                    # WebRTC signaling messages would go here in a full implementation
        
        except Exception as e:
            print(f"❌ WebRTC WebSocket Error: {e}")
            print("🔄 Reconnecting WebRTC in 5 seconds...")
            await asyncio.sleep(5)

async def websocket_client():
    """Handles WebSocket communication with the server."""
    global take_screenshot

    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"pc_id": PC_ID}))
                while True:
                    message = await ws.recv()
                    data = json.loads(message)

                    if data.get("action") == "capture_screenshot" and data.get("pc_id") == PC_ID:
                        print("📸 Screenshot request received! Changing flag to Yes...")
                        take_screenshot = "Yes"
                        send_activity_log()  # ✅ Send logs immediately
                        asyncio.create_task(handle_screenshot())  # ✅ Run screenshot immediately
        except Exception as e:
            print(f"❌ WebSocket Error: {e}")
            print("🔄 Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

async def main():
    """Runs activity monitoring, WebSocket handling, and WebRTC in parallel."""
    await asyncio.gather(
        send_activity(), 
        websocket_client(),
        webrtc_client()
    )

if __name__ == "__main__":
    asyncio.run(main())