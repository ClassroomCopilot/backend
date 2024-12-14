from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_init_user'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from modules.database.tools.neo4j_db_formatter import format_user_email_for_neo_db
import modules.database.init.init_user as init_user
import modules.database.init.init_school as init_school
from modules.database.schemas.entity_neo import StandardUserNode, DeveloperNode, SchoolAdminNode, SchoolNode, TeacherNode, StudentNode, SubjectClassNode, RoomNode, DepartmentNode
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
import json

VALID_USER_TYPES = ['cc_admin', 'cc_email_school_admin', 'cc_ms_school_admin', 'email_school_admin', 'ms_school_admin', 'cc_email_teacher', 'cc_ms_teacher', 'cc_email_student', 'cc_ms_student', 'email_teacher', 'ms_teacher', 'email_student', 'ms_student', 'ms_federated_teacher', 'ms_federated_student', 'standard', 'developer'] # TODO: Implement dev_ user types for pytests, consider use of cc_ user types

router = APIRouter()

@router.post("/create-user")
async def create_user(
    user_id: str = Form(...),
    user_type: str = Form(...),
    user_name: str = Form(...),
    user_email: str = Form(...),
    school_uuid: str = Form(None),
    school_name: str = Form(None),
    school_website: str = Form(None),
    school_path: str = Form(None),
    worker_data: str = Form(None)
):
    logging.info(f"Creating user with user_id: {user_id}, user_type: {user_type}, user_name: {user_name}, user_email: {user_email}")
    
    if school_uuid:
        logging.info(f"School UUID provided: {school_uuid}")
    else:
        logging.info(f"No school UUID provided")
        
    if school_name:
        logging.info(f"School name provided: {school_name}")
    else:
        logging.info(f"No school name provided")
    
    if school_website:
        logging.info(f"School website provided: {school_website}")
    else:
        logging.info(f"No school website provided")
        
    if school_path:
        logging.info(f"School path provided: {school_path}")
    else:
        logging.info(f"No school path provided")
    
    if worker_data:
        logging.info(f"Worker data provided: {worker_data}")
    else:
        logging.info(f"No worker data provided")
    
    # Validate inputs
    if any(param is None for param in (user_type, user_name, user_email, user_id)):
        raise HTTPException(status_code=400, detail=f"Invalid user data")
    
    if user_type not in VALID_USER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid user type: {user_type}")
    
    try:
        # Parse worker data
        worker_data_dict = json.loads(worker_data) if worker_data else None
        
        # Create school node if school data provided
        school_node = None
        if all([school_uuid, school_name, school_website, school_path]):
            school_node = SchoolNode(
                unique_id=f'School_{school_uuid}',
                school_uuid=school_uuid,
                school_name=school_name,
                school_website=school_website,
                path=school_path
            )
        
        # Create user with single database reference
        formatted_email = format_user_email_for_neo_db(user_email)
        user_db_name = f"cc.ccusers.{formatted_email}"
        
        result = init_user.create_user(
            db_name=user_db_name,
            user_id=user_id,
            user_type=user_type,
            username=user_name,
            email=user_email,
            school_node=school_node,
            worker_data=worker_data_dict
        )
        
        # Ensure the result is JSON serializable
        response_data = {
            "status": "success",
            "data": {
                "user_node": result['user_node'],
                "worker_node": result['worker_node'],
                "calendar_nodes": result.get('calendar_nodes')
            }
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logging.error(f"Error creating user in Neo4j: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.post("/create-school")
async def create_school(db_name: str = Form(...), school_uuid: str = Form(...), school_name: str = Form(...), school_website: str = Form(...), school_db_name: str = Form(...)):
    if db_name is None:
        db_name = school_name.replace(" ", "_")
    if school_name is None or school_uuid is None or school_website is None or school_db_name is None:
        logging.error(f"Invalid school data: {school_name}, {school_uuid}, {school_website}, {school_db_name}")
        raise HTTPException(status_code=400, detail="Invalid school data")
    logging.info(f"Creating school {school_name} with school_uuid {school_uuid} and school_website {school_website}")
    return init_school.create_school(db_name, school_uuid, school_name, school_website, school_db_name)

@router.post("/create-department")
async def create_department(
    db_name: str = Form(...),
    unique_id: str = Form(...),
    department_name: str = Form(...),
    department_code: str = Form(...),
    path: str = Form(...)
):
    if db_name is None or unique_id is None or department_name is None or department_code is None or path is None:
        logging.error(f"Invalid department data: {db_name}, {unique_id}, {department_name}, {department_code}, {path}")
        raise HTTPException(status_code=400, detail="Invalid department data")

    department = DepartmentNode(
        unique_id=unique_id,
        department_name=department_name,
        department_code=department_code,
        path=path
    )

    logging.info(f"Creating department {department_name} with unique_id {unique_id}")
    try:
        result = init_school.create_department(db_name, department)
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        logging.error(f"Error creating department: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@router.post("/create-class")
async def create_class(
    db_name: str = Form(...),
    unique_id: str = Form(...),
    subject_class_code: str = Form(...),
    year_group: str = Form(...),
    subject: str = Form(...),
    subject_code: str = Form(...),
    path: str = Form(...)
):
    subject_class_node = SubjectClassNode(
        unique_id=unique_id,
        subject_class_code=subject_class_code,
        year_group=year_group,
        subject=subject,
        subject_code=subject_code,
        path=path
    )
    # Implementation for creating a class
    pass

@router.post("/create-room")
async def create_room(
    db_name: str = Form(...),
    room_unique_id: str = Form(...),
    room_code: str = Form(...),
    path: str = Form(...)
):
    room = RoomNode(
        room_unique_id=room_unique_id,
        room_code=room_code,
        path=path
    )
    # Implementation for creating a room
    pass