import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from levial.config import ConfigManager
from levial.orchestrator import ConversationOrchestrator
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server_v2")

app = FastAPI()

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Initialize orchestrator
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
config_manager = ConfigManager(base_dir=BASE_DIR)
orchestrator = ConversationOrchestrator(config_manager)

# Status callback to broadcast to WebSocket clients
def status_callback(status: str, data: dict):
    """Called by orchestrator to broadcast state changes"""
    message = {"type": status}
    if data:
        message.update(data)
    
    try:
        # Schedule the broadcast in the main event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)
    except Exception as e:
        logger.error(f"Error in status callback: {e}")

orchestrator.set_status_callback(status_callback)

# Run orchestrator in background thread
orchestrator_thread = None

def run_orchestrator():
    """Run the orchestrator's async loop in a thread"""
    try:
        orchestrator.run()
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")

@app.on_event("startup")
async def startup_event():
    global orchestrator_thread
    logger.info("Starting orchestrator in background thread...")
    orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
    orchestrator_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down orchestrator...")
    orchestrator.shutdown_event.set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial connection status
        await websocket.send_json({"type": "connected", "message": "Connected to Levial Voice Agent"})
        
        # Send current user profile
        current_profile = orchestrator.memory_manager.user_profile.get_profile()
        await websocket.send_json({
            "type": "knowledge_update",
            "profile": current_profile
        })
        logger.info(f"Sent initial user profile to client: {current_profile}")
        
        # Keep connection alive and handle any incoming messages
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message: {data}")
            
            # Parse JSON message
            try:
                import json
                message = json.loads(data)
                
                if message.get("type") == "update_knowledge":
                    # Handle manual knowledge update
                    updates = message.get("updates", {})
                    logger.info(f"Processing knowledge update: {updates}")
                    
                    # Update the memory manager
                    new_profile = orchestrator.memory_manager.update_knowledge(updates)
                    
                    # Broadcast update back to all clients
                    await manager.broadcast({
                        "type": "knowledge_update",
                        "profile": new_profile
                    })
                    logger.info(f"Knowledge updated successfully: {new_profile}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Levial Voice Agent Server (Always-On Wake Word Mode)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
