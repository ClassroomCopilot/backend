import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("BACKEND_LOG_PATH"), 'default', True)