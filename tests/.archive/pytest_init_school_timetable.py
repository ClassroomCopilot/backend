from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'pytest_timetable'
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
import modules.database.tools.neontology_tools as neon
import pytest
from fastapi.testclient import TestClient
from routers.database.init.timetable import router
from fastapi import FastAPI
import pandas as pd

app = FastAPI()
app.include_router(router)

client = TestClient(app)

db_name = log_name.replace('_', '')
excel_file = os.environ['EXCEL_TIMETABLE_FILE']
    
@pytest.fixture
def sample_file():
    # Use the existing Excel file to upload
    file_path = excel_file
    logging.info(f"Using sample file at {file_path}")
    yield file_path

def test_upload_school_timetable(sample_file):
    db_name = "pytest_school_timetable_db"
    with open(sample_file, "rb") as f:
        response = client.post(
            "/upload-school-timetable",
            data={"db_name": db_name.replace('_', '')},
            files={"file": (excel_file, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    logging.info(f"Response status code: {response.status_code}")
    logging.info(f"Response JSON: {response.json()}")
    
    assert response.status_code == 200
    response_json = response.json()
    assert "calendar_nodes" in response_json
    assert "school_timetable_nodes" in response_json
    assert response_json["calendar_nodes"] is not None
    assert response_json["school_timetable_nodes"] is not None