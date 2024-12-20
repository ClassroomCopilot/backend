import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
import modules.database.init.init_user as init_user
from modules.database.tools.neo4j_db_formatter import format_user_email_for_neo_db
import modules.database.init.init_school as init_school
import modules.database.init.init_school_timetable as init_school_timetable
import modules.database.init.init_curriculum as init_curriculum
import modules.database.init.xl_tools as xl
from modules.database.schemas.entity_neo import StandardUserNode, DeveloperNode, SchoolAdminNode, SchoolNode, TeacherNode, StudentNode, SubjectClassNode, RoomNode, DepartmentNode
from fastapi import APIRouter, Form, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse
import json

VALID_USER_TYPES = ['cc_admin', 'cc_email_school_admin', 'cc_ms_school_admin', 'email_school_admin', 'ms_school_admin', 'cc_email_teacher', 'cc_ms_teacher', 'cc_email_student', 'cc_ms_student', 'email_teacher', 'ms_teacher', 'email_student', 'ms_student', 'ms_federated_teacher', 'ms_federated_student', 'standard', 'developer'] # TODO: Implement dev_ user types for pytests, consider use of cc_ user types

router = APIRouter()

# Helpers
def initialise_schools_from_config():
        """Initialize a school with the configuration provided from env variables
        """
        default_config = {
            "school_uuid": "kevlarai",
            "school_name": "KevlarAI School",
            "school_website": "https://kevlarai.com",
            "timetable_file": "kevlarai_data/kevlarai_timetable.xlsx",
            "curriculum_file": "kevlarai_data/kevlarai_curriculum.xlsx"
        }
        
        # school_config_str = os.getenv("SCHOOL_CONFIG") # TODO: Implement this
        school_config = default_config
    
        db_name = f"cc.ccschools.{school_config['school_uuid']}"
        
        logger.info(f"Creating database for {school_config['school_name']} using db_name: {db_name}")
        driver = driver_tools.get_driver()
        if driver is None:
            logger.error("Failed to connect to Neo4j")
            return
        
        with driver.session() as session:
            session_tools.create_database(session, db_name)
            logger.debug(f"Database {db_name} created")
        
        # Add filesystem path debugging
        base_path = os.getenv("NODE_FILESYSTEM_PATH")
        schools_path = os.path.join(base_path, "schools")
        school_path = os.path.join(schools_path, f"cc.ccschools.{school_config['school_uuid']}")
        
        logger.debug("Filesystem paths:", {
            "base_path": base_path,
            "schools_path": schools_path,
            "school_path": school_path
        })
        
        # Check if directories exist
        logger.debug("Directory existence check:", {
            "base_exists": os.path.exists(base_path),
            "schools_exists": os.path.exists(schools_path),
            "school_exists": os.path.exists(school_path)
        })
        
        # Create database entry for school without timetable or curriculum
        logger.info(f"Creating school entry for {school_config['school_name']} in database {db_name} without timetable or curriculum")
        result = init_school.create_school(
            db_name=db_name,
            school_uuid=school_config["school_uuid"],
            school_name=school_config["school_name"],
            school_website=school_config["school_website"]
        )
        logger.success(f"{school_config['school_name']} school entry created successfully")
        
        # Create school node from result
        school_node = result['school_node']
        refreshed_school_node = SchoolNode(
            unique_id=school_node.unique_id,
            school_uuid=school_node.school_uuid,
            school_name=school_node.school_name,
            school_website=school_node.school_website,
            path=school_node.path
        )

        # Create timetable entries for school from Excel file
        timetable_file = os.path.join(os.getenv("BACKEND_INIT_PATH"), school_config["timetable_file"])
        
        logger.info(f"Creating timetable entries for {school_config['school_name']} using timetable file: {timetable_file}.")
        school_timetable_dataframes = xl.create_dataframes(timetable_file)
        
        init_school_timetable.create_school_timetable(
            dataframes=school_timetable_dataframes, 
            db_name=db_name, 
            school_node=refreshed_school_node
        )
        logger.success("Timetable entries created successfully")

        # Create curriculum entries for school from Excel file
        curriculum_file = os.path.join(os.getenv("BACKEND_INIT_PATH"), school_config["curriculum_file"])
        
        school_curriculum_dataframes = xl.create_dataframes(curriculum_file)
        
        logger.info(f"Creating curriculum entries for {school_config['school_name']} using curriculum file: {curriculum_file}.")
        init_curriculum.create_curriculum(
            dataframes=school_curriculum_dataframes, 
            db_name=db_name, 
            school_node=refreshed_school_node
        )
        logger.success("Curriculum entries created successfully")


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
    logger.info(f"Creating user with user_id: {user_id}, user_type: {user_type}, user_name: {user_name}, user_email: {user_email}")
    
    if school_uuid:
        logger.info(f"School UUID provided: {school_uuid}")
    else:
        logger.info(f"No school UUID provided")
        
    if school_name:
        logger.info(f"School name provided: {school_name}")
    else:
        logger.info(f"No school name provided")
    
    if school_website:
        logger.info(f"School website provided: {school_website}")
    else:
        logger.info(f"No school website provided")
        
    if school_path:
        logger.info(f"School path provided: {school_path}")
    else:
        logger.info(f"No school path provided")
    
    if worker_data:
        logger.info(f"Worker data provided: {worker_data}")
    else:
        logger.info(f"No worker data provided")
    
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
        logger.error(f"Error creating user in Neo4j: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.post("/create-schools")
async def create_schools():
    initialise_schools_from_config()
    return JSONResponse(content={"status": "success", "message": "Schools created successfully"})

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

    logger.info(f"Creating department {department_name} with unique_id {unique_id}")
    try:
        result = init_school.create_department(db_name, department)
        return JSONResponse(content={"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error creating department: {str(e)}")
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