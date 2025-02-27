from .manager import InitializationManager
from .initialization import InitializationSystem
from modules.logger_tool import initialise_logger
import os

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

def initialize_system() -> None:
    """Initialize the system if needed"""
    init_manager = InitializationManager()
    
    if not init_manager.check_initialization_needed():
        logger.info("No initialization needed")
        return
        
    logger.info("Starting system initialization...")
    
    init_system = InitializationSystem(init_manager)
    success = init_system.run()
    
    if success:
        logger.info("System initialization completed successfully")
    else:
        logger.error("System initialization failed")

__all__ = ['initialize_system', 'InitializationManager', 'InitializationSystem'] 