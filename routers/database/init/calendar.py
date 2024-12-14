from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_init_calendar'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from modules.database.tools.neontology.basenode import BaseNode
import modules.database.init.init_calendar as init_calendar
from fastapi import APIRouter
from datetime import date
from fastapi import HTTPException

router = APIRouter()

@router.post("/create-calendar")
async def create_calendar(db_name: str, start_date: date, end_date: date, attach_to_calendar_node: bool = False, entity_node: BaseNode = None):
    try:
        logging.info(f"Creating calendar for {db_name} from {start_date} to {end_date}")
        if entity_node is None:
            logging.info("No user entity node provided, proceeding without attaching to user entity.")
        return init_calendar.create_calendar(db_name, start_date, end_date, attach_to_calendar_node, entity_node)
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        raise HTTPException(status_code=422, detail=str(e))