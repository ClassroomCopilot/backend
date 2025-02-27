import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(
    log_name='api_main_fastapi',
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_dir=os.getenv("LOG_PATH", "/logs"),
    log_format='default',
    runtime=True
)
from fastapi import FastAPI

def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI application"""
    from fastapi.middleware.cors import CORSMiddleware
    origins = [
        "*",
        "http://localhost:3000",
        f"http://{os.getenv('HOST_FRONTEND')}:{os.getenv('PORT_FRONTEND')}",
        f"http://{os.getenv('HOST_NEO4J')}:{os.getenv('PORT_NEO4J_HTTP')}",
    ]
    logger.debug(f"Setting up CORS with origins: {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

