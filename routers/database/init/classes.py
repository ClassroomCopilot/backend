import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
import pandas as pd
import modules.database.tools.neo4j_driver_tools as driver
from modules.database.tools.neo4j_session_tools import get_node_by_unique_id
import modules.database.init.init_school_timetable as init_school_timetable
import modules.database.init.init_worker_timetable as init_worker_timetable
from modules.database.schemas.entity_neo import SchoolNode, UserNode, TeacherNode
import modules.database.init.xl_tools as xl
import json
import modules.database.tools.neontology_tools as neon

router = APIRouter()

@router.post("/upload-class-list")
async def upload_class_list(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_node: str = Form(...),
    worker_node: str = Form(...)
):
