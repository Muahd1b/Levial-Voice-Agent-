import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")

def test_imports():
    logger.info("Testing imports...")
    try:
        from levial.mcp_client import MCPClient
        logger.info("✅ MCPClient imported")
        
        from levial.memory.vector_store import VectorStore
        logger.info("✅ VectorStore imported")
        
        from levial.memory.user_profile import UserProfile
        logger.info("✅ UserProfile imported")
        
        from levial.memory.manager import MemoryManager
        logger.info("✅ MemoryManager imported")
        
        from levial.tools.calendar_server import mcp as calendar_mcp
        logger.info("✅ Calendar Server imported")
        
        from levial.tools.todoist_server import mcp as todoist_mcp
        logger.info("✅ Todoist Server imported")
        
        from levial.tools.email_manager import mcp as email_mcp
        logger.info("✅ Email Manager imported")
        
        from levial.tools.web_scraper import mcp as scraper_mcp
        logger.info("✅ Web Scraper imported")
        
        from levial.tools.aviation_server import mcp as aviation_mcp
        logger.info("✅ Aviation Server imported")
        
        from levial.tools.sim_monitor import SimMonitor
        logger.info("✅ SimMonitor imported")
        
        from levial.tools.scheduler import mcp as scheduler_mcp
        logger.info("✅ Scheduler imported")
        
        from levial.tools.flashcards import mcp as flashcards_mcp
        logger.info("✅ Flashcards imported")
        
        from levial.agents.researcher import ResearcherAgent
        logger.info("✅ ResearcherAgent imported")
        
        from levial.orchestrator import ConversationOrchestrator
        logger.info("✅ ConversationOrchestrator imported")
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during imports: {e}")
        sys.exit(1)

def test_initialization():
    logger.info("Testing initialization...")
    try:
        # Test Memory Manager
        from levial.memory.manager import MemoryManager
        mm = MemoryManager(Path("./test_artifacts"))
        logger.info("✅ MemoryManager initialized")
        
        # Test SimMonitor
        from levial.tools.sim_monitor import SimMonitor
        sim = SimMonitor()
        logger.info("✅ SimMonitor initialized")
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_imports()
    test_initialization()
    logger.info("🎉 All verification checks passed!")
