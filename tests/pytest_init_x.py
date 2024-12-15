from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
import modules.logger_tool as logger
from routers.database.init.entity_init import router as entity_init_router
from routers.database.init.timetables import router as timetables_router
from routers.database.init.curriculum import router as curriculum_router
from modules.database.schemas.entity_neo import SchoolNode, UserNode
from modules.database.schemas.calendar_neo import CalendarNode

# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "school: mark test as part of school creation"
    )
    config.addinivalue_line(
        "markers", "users: mark test as part of user creation"
    )
    config.addinivalue_line(
        "markers", "timetable: mark test as part of timetable upload"
    )
    config.addinivalue_line(
        "markers", "curriculum: mark test as part of curriculum upload"
    )

# Setup logging
log_name = 'pytest_init_x'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

# Setup FastAPI app and test client
app = FastAPI()
app.include_router(entity_init_router)
app.include_router(timetables_router)
app.include_router(curriculum_router)
client = TestClient(app)

school_timetable_file = os.environ['EXCEL_TIMETABLE_FILE']
school_curriculum_file = os.environ['EXCEL_CURRICULUM_FILE']

@pytest.fixture(scope="module")
def school_info():
    db_name = "cc.ccschools.devschool"
    school_data = {
        "db_name": db_name,
        "school_uuid": "uuid1",
        "school_name": "school1",
        "school_website": "www.school1.com"
    }
    return school_data

@pytest.fixture(scope="module")
def created_school(school_info):
    school_data = school_info
    response = client.post("/create-school", data=school_data)
    logging.info(f"Create school response: {response.json()}")
    assert response.status_code == 200
    logging.success("School created successfully")
    
    response_json = response.json()
    school_node = SchoolNode(**response_json["school_node"])
    
    logging.success(f"School node created: {school_node}")
    return school_node

@pytest.mark.school
def test_create_school(created_school):
    school_node = created_school
    assert school_node is not None

@pytest.mark.users
@pytest.mark.parametrize("user_type, expected_status", [
    ("standard", 200),
    ("developer", 200)
])
def test_create_non_school_user(user_type, expected_status):
    db_name = "cc.users.devusers"
    user_data = {
        "user_type": user_type,
        "user_name": f"test_{user_type}",
        "user_email": f"test_{user_type}@example.com",
        "user_id": f"{user_type}_uuid"
    }
    response = client.post("/create-user", data=user_data)
    assert response.status_code == expected_status
    logging.success(f"{user_type.capitalize()} user created successfully")

@pytest.mark.users
@pytest.mark.parametrize("user_type, expected_status", [
    ("cc_email_school_admin", 200),
    ("cc_email_teacher", 200),
    ("cc_email_student", 200)
])
def test_create_school_user(created_school, user_type, expected_status):
    school_node = created_school
    worker_data = {
        "cc_email_school_admin": {
            "admin_code": "ADM001",
            "admin_name_formal": "Mr. Admin",
            "admin_email": "admin@school.com"
        },
        "cc_email_teacher": {
            "teacher_code": "TCH001",
            "teacher_name_formal": "Ms. Teacher",
            "teacher_email": "teacher@school.com"
        },
        "cc_email_student": {
            "student_code": "STU001",
            "student_name_formal": "Student Name",
            "student_email": "student@school.com"
        }
    }
    user_data = {
        "user_type": user_type,
        "user_name": f"test_{user_type}",
        "user_email": f"test_{user_type}@example.com",
        "user_id": f"{user_type}_uuid",
        "school_uuid": school_node.school_uuid,
        "school_name": school_node.school_name,
        "school_website": school_node.school_website,
        "school_path": school_node.path,
        "worker_data": json.dumps(worker_data[user_type])
    }
    logging.info(f"Sending user data: {user_data}")
    response = client.post("/create-user", data=user_data)
    assert response.status_code == expected_status
    logging.success(f"{user_type.capitalize()} user created successfully")

def test_create_user_invalid_data():
    invalid_user_data = {
        "user_type": "invalid_type",
        "user_name": "test_invalid",
        "user_email": "test_invalid@example.com",
        "user_id": "invalid_uuid"
    }
    response = client.post("/create-user", data=invalid_user_data)
    assert response.status_code == 400
    logging.success("Invalid user data handled correctly")

@pytest.mark.users
def test_create_school_user_without_school_node():
    user_data = {
        "user_type": "cc_email_teacher",
        "user_name": "test_teacher_no_school",
        "user_email": "test_teacher_no_school@example.com",
        "user_id": "teacher_no_school_uuid"
    }
    response = client.post("/create-user", data=user_data)
    assert response.status_code == 400
    logging.success("School-related user without school_node handled correctly")

@pytest.fixture
def sample_file():
    logging.info(f"Using sample file: {school_timetable_file}")
    return school_timetable_file

@pytest.mark.timetable
def test_upload_school_timetable(created_school, sample_file):
    school_node = created_school
    with open(sample_file, "rb") as f:
        response = client.post(
            "/upload-school-timetable",
            data={
                "db_name": "cc.ccschools.devschool",
                "unique_id": school_node.unique_id,
                "school_uuid": school_node.school_uuid,
                "school_name": school_node.school_name,
                "school_db_name": school_node.school_db_name,
                "school_website": school_node.school_website,
                "path": school_node.path
            },
            files={"file": (os.path.basename(sample_file), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    logging.info(f"Timetable upload response: {response.json()}")
    assert response.status_code == 200
    logging.success("Timetable uploaded successfully")
    
    response_json = response.json()
    
    for key in ["school_node", "school_calendar_nodes", "school_timetable_nodes"]:
        assert key in response_json
        logging.success(f"{key} present in response")
    
    school_node = SchoolNode(**response_json["school_node"])
    calendar_node = CalendarNode(**response_json['school_calendar_nodes']['calendar_node'])
    
    logging.success(f"School node validated: {school_node}")
    logging.success(f"Calendar node validated: {calendar_node}")
    
    for key in ["school_node", "school_calendar_nodes", "school_timetable_nodes"]:
        assert response_json[key] is not None
        logging.success(f"{key} is not None")
    
    logging.success("All assertions passed in test_upload_school_timetable")

@pytest.fixture
def curriculum_sample_file():
    logging.info(f"Using curriculum sample file: {school_curriculum_file}")
    return school_curriculum_file


@pytest.mark.curriculum
def test_upload_school_curriculum(created_school, curriculum_sample_file):
    school_node = created_school
    with open(curriculum_sample_file, "rb") as f:
        response = client.post(
            "/upload-school-curriculum",
            data={
                "db_name": "cc.ccschools.devschool",
                "school_uuid": school_node.school_uuid,
                "school_name": school_node.school_name,
                "school_website": school_node.school_website,
                "school_path": school_node.path
            },
            files={"file": (os.path.basename(curriculum_sample_file), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    
    assert response.status_code == 200
    logging.success("Curriculum uploaded successfully")
    
    response_json = response.json()
    
    assert "curriculum_node" in response_json
    assert "pastoral_node" in response_json
    assert "key_stage_nodes" in response_json
    assert "year_group_syllabus_nodes" in response_json
    assert "topic_nodes" in response_json
    assert "topic_lesson_nodes" in response_json
    assert "statement_nodes" in response_json
    
    logging.success("All assertions passed in test_upload_school_curriculum")

@pytest.mark.users
@pytest.mark.timetable
def test_create_kcar_user_and_upload_timetable(created_school):
    school_node = created_school
    user_data = {
        "user_type": "cc_email_teacher",
        "user_name": "K Car",
        "user_email": "kcar@example.com",
        "user_id": "kcar_uuid",
        "school_uuid": school_node.school_uuid,
        "school_name": school_node.school_name,
        "school_website": school_node.school_website,
        "school_path": school_node.path,
        "worker_data": json.dumps({
            "teacher_code": "KCAR",
            "teacher_name_formal": "Mr. K Car",
            "teacher_email": "kcar@example.com"
        })
    }
    logging.info(f"Creating KCar user with data: {user_data}")
    response = client.post("/create-user", data=user_data)
    logging.info(f"KCar user creation response: {response.json()}")
    assert response.status_code == 200
    logging.success("KCar user created successfully")
    kcar_user = UserNode(**response.json()["data"]["user_node"])

    user_timetable_file = os.environ['KCAR_TIMETABLE_URL']
    logging.info(f"User timetable file: {user_timetable_file}")
    with open(user_timetable_file, "rb") as f:
        logging.info(f"Uploading teacher timetable for K Car: {user_timetable_file}")
        response = client.post(
            "/upload-worker-timetable",
            data={
                "user_id": kcar_user.user_id,
                "db_name": "cc.ccschools.devschool"
            },
            files={"file": (os.path.basename(user_timetable_file), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        logging.info(f"Teacher timetable upload response: {response.json()}")
    assert response.status_code == 200
    logging.success("K Car teacher timetable uploaded successfully")
    
    response_json = response.json()
    
    assert response_json["message"] == "Teacher timetable initialized successfully"
    
    logging.success("All assertions passed in test_create_kcar_user_and_upload_timetable")

def pytest_runtest_makereport(item, call):
    if call.when == "call" and call.excinfo is None:
        logging.success(f"Test passed: {item.name}")