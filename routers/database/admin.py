from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_admin'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_http_tools as http
import modules.database.tools.queries as query
from fastapi import APIRouter, Depends, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel
from run.dependencies import admin_dependency
import time

router = APIRouter()

class DatabaseRequest(BaseModel):
    db_name: str

@router.get("/check-database-availability")
async def check_database_availability_endpoint(db_name: str, retries: int = 5, delay: int = 3):
    driver = driver_tools.get_driver()
    if driver is None:
        raise HTTPException(status_code=503, detail="Unable to establish connection with Neo4j")

    check_query = f"SHOW DATABASES WHERE name='{db_name}'"
    for _ in range(retries):
        try:
            logging.info(f"Checking availability for database {db_name}")
            with driver.session(database="system") as session:
                result = session.run(check_query)
                records = result.data()
                if records and records[0].get("currentStatus") == "online":
                    return {"status": "ready"}
                else:
                    logging.error(f"Database {db_name} is not online: {records}")
        except Exception as e:
            logging.error(f"Error checking database availability for {db_name}: {e}")
            time.sleep(delay)
    raise HTTPException(status_code=503, detail="Database not available after retries")

@router.post("/create-database")
async def create_database(db_name: str):
    logging.info(f"Creating database: {db_name}")
    generated_query = query.create_database(db_name)
    logging.info(f"Generated query: {generated_query}")
    return http.send_query(generated_query, encoded_credentials=None, params=None, method="POST", database="system", endpoint="/tx/commit")

@router.post("/stop-database")
async def stop_database(request: DatabaseRequest):
    db_name = request.db_name
    logging.info(f"Stopping database: {db_name}")
    generated_query = query.stop_database(db_name)
    logging.info(f"Generated query: {generated_query}")
    return http.send_query(generated_query, encoded_credentials=None, params=None, method="POST", database="system", endpoint="/tx/commit")

@router.post("/drop-database")
async def drop_database(request: DatabaseRequest):
    db_name = request.db_name
    logging.info(f"Dropping database: {db_name}")
    generated_query = query.drop_database(db_name)
    logging.info(f"Generated query: {generated_query}")
    return http.send_query(generated_query, encoded_credentials=None, params=None, method="POST", database="system", endpoint="/tx/commit")

@router.post("/reset-database")
async def reset_database(db_name: str):
    logging.info(f"Resetting database: {db_name}")
    generated_query = query.reset_database(db_name)
    logging.info(f"Generated query: {generated_query}")
    return http.send_query(generated_query, encoded_credentials=None, params=None, method="POST", database="system", endpoint="/tx/commit")

@router.post("/backup-database")
async def backup_database(admin: bool = Depends(admin_dependency)):
    # Placeholder for database backup logic
    return {"status": "success", "message": "Database backup initiated"}

@router.get("/view-logs")
async def view_logs(admin: bool = Depends(admin_dependency)):
    # Placeholder for log viewing logic
    return {"status": "success", "message": "Logs displayed"}

@router.post("/execute-query")
async def execute_query(query: str, admin: bool = Depends(admin_dependency)):
    # Placeholder for query execution logic
    return {"status": "success", "message": "Query executed"}
