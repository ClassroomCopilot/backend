from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'pytest_calendar'
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
from routers.database.init.calendar import router
from fastapi import FastAPI
from datetime import datetime, timedelta

app = FastAPI()
app.include_router(router)

client = TestClient(app)

# Define a list of date ranges for testing
date_ranges = [
    (datetime.now(), datetime.now() + timedelta(days=1)),  # 1 day
    (datetime.now(), datetime.now() + timedelta(days=7)),  # 1 week
    (datetime.now(), datetime.now() + timedelta(days=30)), # 1 month
    (datetime.now(), datetime.now() + timedelta(days=183)),# 6 months
    (datetime.now(), datetime.now() + timedelta(days=365)) # 1 year
]

# Fixture to manage database name increment
@pytest.fixture(scope="function", autouse=True)
def increment_db_name_counter(request):
    if not hasattr(request.module, "db_name_counter"):
        request.module.db_name_counter = 0
    request.module.db_name_counter += 1
    return request.module.db_name_counter

@pytest.mark.parametrize("start_date, end_date", date_ranges)
def test_create_calendar(start_date, end_date, increment_db_name_counter):
    db_name = f"test_create_calendar_db_{increment_db_name_counter}"
    neo_safe_db_name = db_name.replace("_", "")
    logging.info(f"Creating calendar for {db_name} from {start_date} to {end_date}")
    logging.info(f"Creating calendar for {db_name} from {start_date} to {end_date}")
    response = client.post(
        "/create-calendar",
        params={
            "db_name": neo_safe_db_name,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "calendar_year_nodes" in response_json and response_json["calendar_year_nodes"] != 0
    assert "calendar_month_nodes" in response_json and response_json["calendar_month_nodes"] != 0
    assert "calendar_week_nodes" in response_json and response_json["calendar_week_nodes"] != 0
    assert "calendar_day_nodes" in response_json and response_json["calendar_day_nodes"] != 0