import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
from fastapi import FastAPI
import uvicorn

from run.setup import setup_cors
from run.routers import register_routes
from run.initialization import initialize_system

try:
    # Run initialization if needed
    initialize_system()
except Exception as e:
    logger.error(f"Initialization failed: {str(e)}")
    # Don't fail startup if initialization fails
    pass

# FastAPI App Setup
app = FastAPI()
setup_cors(app)

# Register routes
register_routes(app)

if __name__ == "__main__":
    import uvicorn
    import os

    if os.getenv('DEV_MODE') == 'true':
        logger.info("Running with Reload")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv('PORT_BACKEND')),
            reload=True
        )
    else:
        logger.info("Running without Reload")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv('PORT_BACKEND')),
        )
