from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_calendar_get_events'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import modules.database.tools.neo4j_driver_tools as driver
from fastapi import APIRouter, HTTPException
import colorsys
import random

# Predefined vibrant color palette
BASE_COLORS = [
    "#FF4136", "#FF851B", "#FFDC00", "#2ECC40", "#0074D9", "#B10DC9",
    "#F012BE", "#FF6F61", "#7FDBFF", "#01FF70", "#001f3f", "#85144b",
    "#39CCCC", "#3D9970", "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71",
    "#1abc9c", "#3498db", "#9b59b6", "#34495e", "#16a085", "#27ae60",
    "#2980b9", "#8e44ad", "#2c3e50", "#d35400", "#c0392b", "#bdc3c7",
    "#7f8c8d", "#00a86b", "#8B4513", "#4B0082", "#800000", "#1E90FF"
]

def generate_vibrant_color():
    h = random.random()
    s = 0.5 + random.random() * 0.5  # 0.5 to 1.0
    v = 0.5 + random.random() * 0.5  # 0.5 to 1.0
    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]
    return f"#{r:02x}{g:02x}{b:02x}"

# Extend the color palette
EXTENDED_COLOR_PALETTE = BASE_COLORS + [generate_vibrant_color() for _ in range(100)]

def get_subject_class_color(subject_class):
    # Use a hash function to generate a unique number for each subject class
    hash_value = hash(subject_class)
    
    # Use the hash to select a color from the extended palette
    color_index = hash_value % len(EXTENDED_COLOR_PALETTE)
    color = EXTENDED_COLOR_PALETTE[color_index]
    
    return color

router = APIRouter()

@router.get("/get_teacher_timetable_events")
async def get_teacher_timetable_events(
    unique_id: str,
    worker_db_name: str
):
    logging.info(f"Getting timetable events for teacher {unique_id} from database {worker_db_name}")
    neo_driver = driver.get_driver(db_name=worker_db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=worker_db_name) as neo_session:
            query = """
            MATCH (t:Teacher {unique_id: $unique_id})-[:TEACHER_HAS_TIMETABLE]->(tt:TeacherTimetable)
            -[:TIMETABLE_HAS_CLASS]->(sc:SubjectClass)-[:CLASS_HAS_LESSON]->(tl:TimetableLesson)
            RETURN tl.unique_id as id, 
                   tl.period_code as period_code,
                   COALESCE(sc.subject_class_code, 'Untitled Class') as subject_class, 
                   tl.date as date, 
                   tl.start_time as start_time, 
                   tl.end_time as end_time,
                   tl.path as path
            """
            result = neo_session.run(query, unique_id=unique_id)
            
            events = []
            for record in result:
                start = f"{record['date']}T{record['start_time']}"
                end = f"{record['date']}T{record['end_time']}"
                title = f"{record['subject_class']}"
                events.append({
                    "id": record["id"],
                    "title": title,
                    "start": start,
                    "end": end,
                    "groupId": f"subject-class-{record['subject_class']}",
                    "extendedProps": {
                        "subjectClass": record['subject_class'],
                        "color": get_subject_class_color(record['subject_class']),
                        "periodCode": record['period_code'],
                        "path": record['path']
                    }
                })
            logging.info(f"Found {len(events)} events for teacher {unique_id}")
            return {"status": "success", "events": events}
    except Exception as e:
        logging.error(f"Error fetching events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)
