import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

# WebRTC router
webrtc_router = APIRouter()

# Connected WebRTC clients
senders: Dict[str, WebSocket] = {}  # PC_ID -> WebSocket
viewers: Dict[str, List[WebSocket]] = {}  # PC_ID -> List of viewer WebSockets

@webrtc_router.websocket("/webrtc")
async def webrtc_endpoint(websocket: WebSocket):
    """Handles WebRTC WebSocket connections for video streaming."""
    await websocket.accept()
    
    # Variables to track this connection
    pc_id = None
    client_type = None
    
    try:
        # First message should be registration
        data = await websocket.receive_text()
        message = json.loads(data)
        
        if message.get("type") == "register":
            pc_id = message.get("pc_id")
            client_type = message.get("client_type")
            
            if not pc_id:
                await websocket.close(code=1008, reason="Missing PC ID")
                return
                
            if client_type == "sender":
                # Register as video sender (monitored PC)
                senders[pc_id] = websocket
                print(f"✅ New sender registered: {pc_id}")
                
                # Create viewers list if it doesn't exist
                if pc_id not in viewers:
                    viewers[pc_id] = []
                    
            elif client_type == "viewer":
                # Register as video viewer (dashboard)
                if pc_id not in viewers:
                    viewers[pc_id] = []
                    
                viewers[pc_id].append(websocket)
                print(f"✅ New viewer registered for {pc_id}")
                
                # Notify the sender to start streaming if it's connected
                if pc_id in senders:
                    await senders[pc_id].send_text(json.dumps({
                        "type": "start-stream",
                        "pc_id": pc_id
                    }))
            
            # Main message handling loop
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if client_type == "sender" and message.get("type") == "video-frame":
                    # Forward video frames to all viewers of this PC
                    if pc_id in viewers and viewers[pc_id]:
                        frame_data = json.dumps({
                            "type": "video-frame",
                            "pc_id": pc_id,
                            "frame": message.get("frame"),
                            "timestamp": message.get("timestamp")
                        })
                        
                        # Send to all viewers
                        for viewer in viewers[pc_id][:]:  # Use a copy of the list for iteration
                            try:
                                await viewer.send_text(frame_data)
                            except Exception:
                                # Remove disconnected viewers
                                if viewer in viewers[pc_id]:
                                    viewers[pc_id].remove(viewer)
                
                elif client_type == "viewer" and message.get("type") == "viewer-command":
                    # Forward viewer commands to the sender
                    command = message.get("command")
                    if pc_id in senders:
                        await senders[pc_id].send_text(json.dumps({
                            "type": command,
                            "pc_id": pc_id
                        }))
                
    except WebSocketDisconnect:
        print(f"WebRTC client disconnected: {pc_id} ({client_type})")
    except Exception as e:
        print(f"❌ WebRTC Error: {e}")
    finally:
        # Clean up on disconnect
        if client_type == "sender" and pc_id in senders:
            del senders[pc_id]
            
            # Notify viewers that the stream has ended
            if pc_id in viewers:
                for viewer in viewers[pc_id][:]:
                    try:
                        await viewer.send_text(json.dumps({
                            "type": "stream-ended",
                            "pc_id": pc_id
                        }))
                    except:
                        pass
                        
        elif client_type == "viewer" and pc_id in viewers:
            if websocket in viewers[pc_id]:
                viewers[pc_id].remove(websocket)
                
            # If no more viewers, tell sender to stop streaming
            if pc_id in senders and not viewers[pc_id]:
                try:
                    await senders[pc_id].send_text(json.dumps({
                        "type": "stop-stream",
                        "pc_id": pc_id
                    }))
                except:
                    pass
        
        print(f"WebRTC connection closed: {pc_id} ({client_type})")