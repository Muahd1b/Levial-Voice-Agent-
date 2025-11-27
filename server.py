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

# Configuration for orchestrator
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
config_manager = ConfigManager(base_dir=BASE_DIR)

# Store orchestrator instance (recreated on each start)
orchestrator = None

# Store the main event loop reference for cross-thread callback
main_loop = None

# Status callback to broadcast to WebSocket clients
def status_callback(status: str, data: dict):
    """Called by orchestrator to broadcast state changes"""
    message = {"type": status}
    if data:
        message.update(data)
    
    try:
        # Use the stored main loop reference
        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), main_loop)
    except Exception as e:
        logger.error(f"Error in status callback: {e}")

# Run orchestrator in background thread
orchestrator_thread = None
orchestrator_running = False  # Track if orchestrator is actively running

def run_orchestrator():
    """Run the orchestrator's async loop in a thread"""
    global orchestrator
    try:
        orchestrator.run()
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
    finally:
        global orchestrator_running
        orchestrator_running = False

@app.on_event("startup")
async def startup_event():
    global main_loop
    logger.info("Server starting. Orchestrator will start on demand.")
    main_loop = asyncio.get_event_loop()  # Capture the main event loop

@app.on_event("shutdown")
async def shutdown_event():
    global orchestrator_running
    if orchestrator_running:
        logger.info("Shutting down orchestrator...")
        orchestrator.shutdown_event.set()
        if orchestrator_thread:
            orchestrator_thread.join(timeout=5)

@app.get("/status")
async def get_status():
    """Return server and agent status"""
    return {
        "server_running": True,
        "agent_running": orchestrator_running
    }

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
                    if orchestrator is None:
                        logger.warning("Orchestrator not running, cannot update knowledge")
                        continue
                        
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
                    
                elif message.get("type") == "update_config":
                    # Handle configuration update
                    if orchestrator is None:
                        logger.warning("Orchestrator not running, cannot update config")
                        continue
                        
                    config = message.get("config", {})
                    logger.info(f"Processing config update: {config}")
                    
                    # Update the orchestrator config
                    orchestrator.update_config(config)
                    logger.info(f"Config updated successfully")
                    
                elif message.get("type") == "trigger_wake":
                    # Handle manual wake trigger
                    if orchestrator is None:
                        logger.warning("Orchestrator not running, cannot trigger wake")
                        continue
                        
                    logger.info("Received manual wake trigger")
                    orchestrator.trigger_wake()
                    
                elif message.get("type") == "start_agent":
                    # Handle agent start request
                    global orchestrator_thread, orchestrator_running, orchestrator
                    if not orchestrator_running:
                        logger.info("Starting orchestrator...")
                        
                        # Create a new orchestrator instance
                        orchestrator = ConversationOrchestrator(config_manager)
                        orchestrator.set_status_callback(status_callback)
                        
                        # Start orchestrator in new thread
                        orchestrator_thread = threading.Thread(target=run_orchestrator, daemon=True)
                        orchestrator_thread.start()
                        orchestrator_running = True
                        
                        await manager.broadcast({
                            "type": "agent_started"
                        })
                        logger.info("Agent started successfully")
                    else:
                        logger.warning("Agent is already running")
                        
                elif message.get("type") == "stop_agent":
                    # Handle agent stop request
                    if orchestrator_running:
                        logger.info("Stopping orchestrator...")
                        orchestrator.shutdown_event.set()
                        if orchestrator_thread:
                            orchestrator_thread.join(timeout=5)
                        orchestrator_running = False
                        await manager.broadcast({
                            "type": "agent_stopped"
                        })
                        logger.info("Agent stopped successfully")
                    else:
                        logger.warning("Agent is not running")
                    
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
