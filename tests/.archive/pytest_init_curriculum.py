from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'pytest_init_curriculum'
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
from routers.database.init.curriculum import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app)

db_name = log_name.replace('_', '')
excel_file = os.environ['EXCEL_CURRICULUM_FILE']

driver = driver_tools.get_driver(database=db_name)
neon.init_neontology_connection()
    
@pytest.fixture
def sample_file():
    # Use the existing Excel file to upload
    file_path = excel_file
    logging.info(f"Using sample file at {file_path}")
    yield file_path

def test_upload_curriculum(sample_file):
    db_name = "test_curriculum_db"
    with open(sample_file, "rb") as f:
        response = client.post(
            "/upload-curriculum",
            files={"file": (excel_file, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"db_name": db_name.replace('_', '')}
        )
    logging.info(f"Response status code: {response.status_code}")
    logging.info(f"Response JSON: {response.json()}")
    
    assert response.status_code == 200
    response_json = response.json()
    logging.info(f"Response JSON keys: {response_json.keys()}")
    
    # Adjust the assertions based on the actual response structure
    assert "status" in response_json or "12" in response_json
    if "status" in response_json:
        assert response_json["status"] == "Success"
    else:
        assert "created" in response_json["12"]
        assert "merged" in response_json["12"]