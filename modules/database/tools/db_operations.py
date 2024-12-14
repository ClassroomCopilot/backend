from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_db_operations'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi.testclient import TestClient
from fastapi import HTTPException
import time
from neo4j import GraphDatabase

class DatabaseNotFoundError(Exception):
    """Exception raised when the specified database cannot be found."""
    def __init__(self, db_name):
        super().__init__(f"Database '{db_name}' not found.")

# Dev ??
def get_client():
    from main import app  # Delayed import to avoid circular dependency
    return TestClient(app)

# Ops ??
def stop_database(db_name):
    client = get_client()
    try:
        logging.debug(f"Stopping database {db_name}")
        response = client.post("/database/admin/stop-database", json={"db_name": db_name})
    except DatabaseNotFoundError:
        logging.info(f"Database {db_name} not found when attempting to stop. Skipping.")
    else:
        logging.info(response.text)
    return response

def drop_database(db_name):
    client = get_client()
    try:
        response = client.post("/database/admin/drop-database", json={"db_name": db_name})
    except DatabaseNotFoundError:
        logging.info(f"Database {db_name} not found when attempting to drop. Skipping.")
    else:
        logging.info(response.text)
    return response

def create_database(db_name):
    client = get_client()
    response = client.post("/database/admin/create-database", params={"db_name": db_name})
    logging.info(response.text)
    return response

def check_database_availability(db_name, retries=5, delay=5):  # Increased delay
    client = get_client()
    attempt = 0
    while attempt < retries:
        try:
            logging.info(f"Attempt {attempt + 1}: Checking availability for database {db_name}")
            response = client.get(f"/check-database-availability?db_name={db_name}")
            if response.status_code == 200 and response.json().get('status') == "ready":
                logging.info(f"Database {db_name} is ready.")
                return response.json()
            else:
                logging.error(f"Database {db_name} is not available: {response.text}")
        except Exception as e:
            logging.error(f"Error checking database availability for {db_name} on attempt {attempt + 1}: {e}")
        time.sleep(delay)  # Increased delay before the next retry
        attempt += 1
    raise HTTPException(status_code=503, detail="Database availability check failed after retries")