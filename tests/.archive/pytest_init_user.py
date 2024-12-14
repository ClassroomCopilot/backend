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
from fastapi import FastAPI
import pandas as pd

# Import the router from entity_init.py
from routers.database.init.entity_init import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)

@pytest.mark.parametrize("username, email, user_id", [
    ("user1", "user1@example.com", "uuid1"),
    ("user2", "user2@example.com", "uuid2"),
    ("user3", "user3@example.com", "uuid3")
])
def test_create_user(username, email, user_id):
    response = client.post(
        "/create-user",
        data={"username": username, "email": email, "user_id": user_id}
    )
    logging.info(f"Tested creating user {username}. Response status code: {response.status_code}")
    response_json = response.json()
    logging.info(f"Response JSON: {response_json}")

    assert response.status_code == 200