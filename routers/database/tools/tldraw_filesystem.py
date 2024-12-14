from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_tools_tldraw_filesystem'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter, HTTPException, Query
from typing import Dict
import json
from fastapi.middleware.cors import CORSMiddleware

from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from modules.database.schemas.entity_neo import UserNode
from modules.database.tools.neo4j_db_formatter import format_user_email_for_neo_db

router = APIRouter()

@router.post("/get_tldraw_user_node_file")
async def read_tldraw_user_node_file(user_node: UserNode):
    logging.debug(f"Reading tldraw file for user node: {user_node.user_email}")
    
    # Format the database name using the email
    formatted_email = format_user_email_for_neo_db(user_node.user_email)
    db_name = f"cc.ccusers.{formatted_email}"
    
    fs = ClassroomCopilotFilesystem(db_name=db_name, init_run_type="user")
    
    logging.debug(f"Filesystem root path: {fs.root_path}")
    
    # Handle path based on environment
    if os.getenv("DEV_MODE") == "true":
        # In dev mode, use the full system path from the node
        if not user_node.path:
            raise HTTPException(status_code=400, detail="Node path not found")
        logging.debug(f"Using DEV_MODE path: {user_node.path}")
        base_path = os.path.normpath(user_node.path)
    else:
        # In prod mode, construct path using formatted email
        logging.warning(f"Using db_name as base path not ready in prod: {db_name}")
        base_path = formatted_email
    
    # Construct final path including tldraw file
    logging.debug(f"Base path: {base_path}")
    file_path = os.path.join(base_path, "tldraw_file.json")
    logging.debug(f"File path: {file_path}")
    file_location = os.path.normpath(os.path.join(fs.root_path, file_path))
    logging.debug(f"File location: {file_location}")
    
    logging.debug(f"Attempting to read file at: {file_location}")
    
    if os.path.exists(file_location):
        logging.debug(f"File exists: {file_location}")
        try:
            with open(file_location, "r") as file:
                data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from file: {e}")
            raise HTTPException(status_code=500, detail="Invalid JSON in file")
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            raise HTTPException(status_code=500, detail="Error reading file")
    else:
        logging.debug(f"File does not exist: {file_location}")
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/set_tldraw_user_node_file")
async def set_tldraw_user_node_file(user_node: UserNode, data: Dict):
    logging.debug(f"Setting tldraw file for user node: {user_node.user_email}")
    
    # Format the database name using the email
    formatted_email = format_user_email_for_neo_db(user_node.user_email)
    db_name = f"cc.ccusers.{formatted_email}"
    
    fs = ClassroomCopilotFilesystem(db_name=db_name, init_run_type="user")
    
    # Handle path based on environment
    if os.getenv("ENVIRONMENT") == "dev":
        # In dev mode, use the full system path from the node
        if not user_node.path:
            raise HTTPException(status_code=400, detail="Node path not found")
        base_path = os.path.normpath(user_node.path)
    else:
        # In prod mode, construct path using formatted email
        base_path = formatted_email
    
    # Construct final path including tldraw file
    file_path = os.path.join(base_path, "tldraw_file.json")
    file_location = os.path.normpath(os.path.join(fs.root_path, file_path))
    
    logging.debug(f"Attempting to write file at: {file_location}")
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        
        # Write the file
        with open(file_location, "w") as file:
            json.dump(data, file)
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error writing file: {e}")
        raise HTTPException(status_code=500, detail="Error writing file")

@router.get("/get_tldraw_node_file")
async def read_tldraw_node_file(path: str, db_name: str):
    logging.debug(f"Reading tldraw file for path: {path}")
    
    fs = ClassroomCopilotFilesystem(db_name=db_name, init_run_type="user")
    
    logging.debug(f"Filesystem root path: {fs.root_path}")
    
    # Handle path based on environment
    if os.getenv("DEV_MODE") == "true":
        # In dev mode, use the full system path from the node
        if not path:
            raise HTTPException(status_code=400, detail="Path not provided")
        logging.debug(f"Using DEV_MODEpath: {path}")
        base_path = os.path.normpath(path)
    else:
        # In prod mode, construct path
        logging.warning(f"Using db_name as base path not ready in prod: {db_name}")
        base_path = db_name
    
    # Construct final path including tldraw file
    logging.debug(f"Base path: {base_path}")
    file_path = os.path.join(base_path, "tldraw_file.json")
    logging.debug(f"File path: {file_path}")
    file_location = os.path.normpath(os.path.join(fs.root_path, file_path))
    logging.debug(f"File location: {file_location}")
    
    logging.debug(f"Attempting to read file at: {file_location}")
    
    if os.path.exists(file_location):
        logging.debug(f"File exists: {file_location}")
        try:
            with open(file_location, "r") as file:
                data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from file: {e}")
            raise HTTPException(status_code=500, detail="Invalid JSON in file")
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            raise HTTPException(status_code=500, detail="Error reading file")
    else:
        logging.debug(f"File does not exist: {file_location}")
        raise HTTPException(status_code=404, detail="File not found")

@router.post("/set_tldraw_node_file")
async def set_tldraw_node_file(path: str, db_name: str, data: Dict):
    logging.debug(f"Setting tldraw file for path: {path}")
    
    fs = ClassroomCopilotFilesystem(db_name=db_name, init_run_type="user")
    
    logging.debug(f"Filesystem root path: {fs.root_path}")
    
    # Handle path based on environment
    if os.getenv("DEV_MODE") == "true":
        # In dev mode, use the full system path from the node
        if not path:
            raise HTTPException(status_code=400, detail="Path not provided")
        logging.debug(f"Using DEV_MODEpath: {path}")
        base_path = os.path.normpath(path)
    else:
        # In prod mode, construct path
        logging.warning(f"Using db_name as base path not ready in prod: {db_name}")
        base_path = db_name
    
    # Construct final path including tldraw file
    logging.debug(f"Base path: {base_path}")
    file_path = os.path.join(base_path, "tldraw_file.json")
    logging.debug(f"File path: {file_path}")
    file_location = os.path.normpath(os.path.join(fs.root_path, file_path))
    logging.debug(f"File location: {file_location}")
    
    logging.debug(f"Attempting to set file at: {file_location}")
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_location), exist_ok=True)
        
        # Write the file
        with open(file_location, "w") as file:
            json.dump(data, file)
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error writing file: {e}")
        raise HTTPException(status_code=500, detail="Error writing file")
