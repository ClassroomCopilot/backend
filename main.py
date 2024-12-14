import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("BACKEND_LOG_PATH"), 'default', True)
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import jwt
from jwt.exceptions import InvalidTokenError

from run.setup import setup_cors, initialize_application
from run.routers import register_routes
from run.frontend import setup_frontend

# FastAPI App Setup
initialize_application()
app = FastAPI()
setup_cors(app)
register_routes(app)

if __name__ == "__main__":
    import uvicorn
    import os

    if os.getenv('VITE_DEV') == 'true':
        logger.debug("Running without Nginx")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv('VITE_FASTAPI_PORT')),
            reload=True
        )
    else:
        logger.debug("Running with Nginx")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(os.getenv('VITE_FASTAPI_PORT')),
        )
