from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_init_curriculum'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import modules.database.init.xl_tools as xl
import modules.database.init.init_curriculum as init_curriculum
from modules.database.schemas.entity_neo import SchoolNode
from fastapi import APIRouter, File, UploadFile, Form

router = APIRouter()

@router.post("/upload-curriculum")
async def upload_curriculum(file: UploadFile = File(...), db_name: str = Form(...)):
    if file.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        return {"status": "Error", "message": "Invalid file format"}
    logging.info(f"Uploading curriculum for {db_name}")
    dataframes = xl.create_dataframes_from_fastapiuploadfile(file)
    return init_curriculum.create_curriculum(db_name, dataframes)

@router.post("/upload-school-curriculum")
async def upload_school_curriculum(
    file: UploadFile = File(...),
    db_name: str = Form(...),
    school_uuid: str = Form(...),
    school_name: str = Form(...),
    school_website: str = Form(...),
    school_path: str = Form(...)
):
    if file.content_type != 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        return {"status": "Error", "message": "Invalid file format"}
    logging.info(f"Uploading curriculum for school {school_name} in {db_name}")
    dataframes = xl.create_dataframes_from_fastapiuploadfile(file)
    school_node = SchoolNode(
        unique_id=f'School_{school_uuid}',
        school_uuid=school_uuid,
        school_name=school_name,
        school_website=school_website,
        path=school_path
    )
    return init_curriculum.create_curriculum(db_name, dataframes, school_node)