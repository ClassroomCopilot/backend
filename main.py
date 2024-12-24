import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
from fastapi import FastAPI
import uvicorn

from run.setup import setup_cors
from run.routers import register_routes

# FastAPI App Setup
app = FastAPI()
setup_cors(app)
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
