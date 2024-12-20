from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_init_schools'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
import pandas as pd
import modules.database.tools.neo4j_driver_tools as driver
from modules.database.tools.neo4j_session_tools import get_node_by_unique_id
import modules.database.init.init_school_timetable as init_school_timetable
import modules.database.init.init_worker_timetable as init_worker_timetable
from modules.database.schemas.entity_neo import SchoolNode
import modules.database.init.xl_tools as xl
import json

router = APIRouter()

@router.post("/upload-school-timetable")
async def upload_school_timetable(
    file: UploadFile = File(...),
    db_name: str = Form(...),
    unique_id: str = Form(...),
    school_uuid: str = Form(...),
    school_name: str = Form(...),
    school_website: str = Form(...),
    path: str = Form(...)
):
    school_node = SchoolNode(
        unique_id=unique_id,
        school_uuid=school_uuid,
        school_name=school_name,
        school_website=school_website,
        path=path
    )
    if file.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        return {"status": "Error", "message": "Invalid file format"}
    logging.info(f"Uploading timetable for {db_name} from {file.filename}")
    dataframes = xl.create_dataframes_from_fastapiuploadfile(file)
    return init_school_timetable.create_school_timetable(dataframes, db_name, school_node)

@router.post("/upload-worker-timetable")
async def upload_worker_timetable(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    worker_node: str = Form(...)
):
    if file.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        raise HTTPException(status_code=422, detail="Invalid file format")
    
    try:
        worker_node_data = json.loads(worker_node)
        logging.info(f"Uploading worker timetable for {worker_node_data['teacher_code']} from {file.filename} for {worker_node_data['worker_db_name']}")
        logging.debug(f"Worker node data: {worker_node_data}")
        
        # Read file content into memory
        file_content = await file.read()
        
        # Schedule the processing of the timetable in the background
        background_tasks.add_task(
            process_worker_timetable,
            file_content,
            worker_node_data
        )
        
        return {
            "status": "Accepted",
            "message": "Processing of teacher timetable started"
        }
    except Exception as e:
        logging.error(f"Error handling timetable upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_worker_timetable(file_content, worker_node_data):
    neo_driver = driver.get_driver(db_name=worker_node_data['worker_db_name'])
    if neo_driver is None:
        logging.error(f"Failed to connect to the database {worker_node_data['worker_db_name']}")
        return
    
    try:
        # Create a DataFrame from the file content
        from io import BytesIO
        timetable_df = pd.read_excel(BytesIO(file_content))
        
        # Get the school version of the worker node
        logging.info(f"Getting school worker node for {worker_node_data['unique_id']} from {worker_node_data['worker_db_name']}")
        
        with neo_driver.session(database=worker_node_data['worker_db_name']) as neo_session:
            school_worker_node = get_node_by_unique_id(session=neo_session, unique_id=worker_node_data['unique_id'])
            
            if school_worker_node is None:
                error_msg = f"School worker node not found for unique_id: {worker_node_data['unique_id']}"
                logging.error(error_msg)
                raise Exception(error_msg)
                
            logging.debug(f"School worker node found: {school_worker_node}")
            
            logging.info(f"Initializing worker timetable for school worker: {school_worker_node['teacher_code']}")
            init_worker_timetable.init_worker_timetable(timetable_df, school_worker_node)
            logging.info(f"Worker timetable initialized for school worker: {school_worker_node['teacher_code']}")
            
    except Exception as e:
        logging.error(f"Error processing worker timetable: {str(e)}")
        raise
    finally:
        logging.info(f"Closing driver for {worker_node_data['worker_db_name']}")
        driver.close_driver(neo_driver)