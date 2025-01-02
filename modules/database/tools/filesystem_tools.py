from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_filesystem_tools'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from datetime import timedelta
import json
import re

class ClassroomCopilotFilesystem:
    def __init__(self, db_name: str, init_run_type: str = None):
        logging.info(f"Initializing ClassroomCopilotFilesystem with db_name: {db_name} and init_run_type: {init_run_type}")
        
        self.db_name = db_name
        
        # Get base path from environment
        self.base_path = os.getenv("NODE_FILESYSTEM_PATH")
        if not self.base_path:
            raise ValueError("NODE_FILESYSTEM_PATH environment variable not set")
        
        # Set root path based on init type
        if init_run_type == "school":
            self.root_path = os.path.join(self.base_path, "schools", self.db_name)
            logging.debug(f"School root path: {self.root_path}")
        elif init_run_type == "user":
            self.root_path = os.path.join(self.base_path, "users", self.db_name)
            logging.debug(f"User root path: {self.root_path}")
        elif init_run_type == "multiplayer":
            self.root_path = os.path.join(self.base_path, "multiplayer")
            logging.debug(f"Multiplayer root path: {self.root_path}")
        else:
            self.root_path = os.path.join(self.base_path, self.db_name)
            logging.debug(f"Default root path: {self.root_path}")
        
        # Ensure root directory exists
        os.makedirs(self.root_path, exist_ok=True)
        
        logging.debug(f"Filesystem initialized with run type: {init_run_type} and root path: {self.root_path}")

    def log_directory_structure(self, start_path):
        for root, dirs, files in os.walk(start_path):
            level = root.replace(start_path, '').count(os.sep)
            indent = ' ' * 4 * (level)
            logging.info(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                logging.info(f"{subindent}{f}")
                
    def create_directory(self, path):
        """Utility method to create a directory if it doesn't exist."""
        if not os.path.exists(path):
            os.makedirs(path)
            logging.info(f"Directory {path} created.")
            return True
        return False

    def sanitize_username(self, username):
        return re.sub(r'[^\w\-_\.]', '_', username)

    def create_user_directory(self, username, user_type=None, school_path=None):
        """Create a directory for a specific user."""
        sanitized_username = self.sanitize_username(username)
        
        if school_path:
            # For school database: /schools/[school_db]/users/[user_type]/[username]
            user_path = os.path.join(self.root_path, "users", user_type, sanitized_username)
        else:
            # For user database: /users/[user_db]/[username]
            user_path = os.path.join(self.root_path, sanitized_username)
            
        logging.info(f"Creating user directory at {user_path}")
        return self.create_directory(user_path), user_path
    
    def create_user_worker_directory(self, user_path, worker_code):
        """Create a worker directory under the user directory."""
        # Create worker directory: [user_path]/[worker_code]
        worker_path = os.path.join(user_path, worker_code)
        logging.info(f"Creating worker directory at {worker_path}")
        return self.create_directory(worker_path), worker_path
    
    def create_school_worker_directory(self, school_path, worker_type):
        """Create a worker directory under the school directory."""
        worker_path = os.path.join(school_path, "workers", worker_type)
        logging.info(f"Creating school worker directory at {worker_path}")
        return self.create_directory(worker_path), worker_path
    
    def create_school_directory(self, school_uuid=None):
        """Create a directory for a specific school."""
        logging.info(f"Creating school directory with school_uuid: {school_uuid}")
        if school_uuid is None:
            logging.debug(f"School UUID is None, creating school directory at {self.root_path}")
            school_path = self.root_path
        else:
            logging.debug(f"School UUID is not None, creating school directory at {os.path.join(self.root_path, school_uuid)}")
            school_path = os.path.join(self.root_path, school_uuid)
        return self.create_directory(school_path), school_path
    
    def create_year_directory(self, year, calendar_path=None):
        """Create a directory for a specific year."""
        if calendar_path is None:
            year_path = os.path.join(self.root_path, "calendar", str(year))
        else:
            year_path = os.path.join(calendar_path, "years", str(year))

        return self.create_directory(year_path), year_path

    def create_month_directory(self, year, month, calendar_path=None):
        """Create a directory for a specific month."""
        if calendar_path is None:
            month_path = os.path.join(self.root_path, "calendar", str(year), "months", f"{month:02}")
        else:
            month_path = os.path.join(calendar_path, "years", str(year), "months", f"{month:02}")

        return self.create_directory(month_path), month_path

    def create_week_directory(self, year, week, calendar_path=None):
        """Create a directory for a specific week."""
        if calendar_path is None:
            week_path = os.path.join(self.root_path, "calendar", str(year), "weeks", f"{week}")
        else:
            week_path = os.path.join(calendar_path, "years", str(year), "weeks", f"{week}")

        return self.create_directory(week_path), week_path

    def create_day_directory(self, year, month, day, calendar_path=None):
        """Create a directory for a specific day."""
        if calendar_path is None:
            day_path = os.path.join(self.root_path, "calendar", str(year), "months", f"{month:02}", f"{day:02}")
        else:
            day_path = os.path.join(calendar_path, "years", str(year), "months", f"{month:02}", f"{day:02}")

        return self.create_directory(day_path), day_path

    def setup_calendar_directories(self, start_date, end_date, calendar_path=None):
        """Setup directories for the range from start_date to end_date."""
        current_date = start_date
        while current_date <= end_date:
            year, month, day = current_date.year, current_date.month, current_date.day
            if calendar_path is None:
                _, year_path = self.create_year_directory(year)
                _, month_path = self.create_month_directory(year, month)
                _, week_path = self.create_week_directory(year, current_date.isocalendar()[1])
                _, day_path = self.create_day_directory(year, month, day)
            else:
                _, year_path = self.create_year_directory(year, calendar_path)
                _, month_path = self.create_month_directory(year, month, calendar_path)
                _, week_path = self.create_week_directory(year, current_date.isocalendar()[1], calendar_path)
                _, day_path = self.create_day_directory(year, month, day, calendar_path)
            current_date += timedelta(days=1)
        return year_path, month_path, week_path, day_path

    def create_school_timetable_directory(self, school_path=None):
        """Create a directory for the timetable."""
        if school_path is None:
            timetable_path = os.path.join(self.root_path, "timetable")
        else:
            timetable_path = os.path.join(school_path, "timetable")

        return self.create_directory(timetable_path), timetable_path

    def create_school_timetable_year_directory(self, timetable_path, year):
        """Create a directory for a specific academic year within the timetable."""
        year_path = os.path.join(timetable_path, "years", str(year))
        return self.create_directory(year_path), year_path

    def create_school_timetable_academic_term_directory(self, timetable_path, term_name, term_number):
        """Create a directory for a specific term within an academic year."""
        term_path = os.path.join(timetable_path, "terms", f"{term_number}_{term_name.replace(' ', '_')}")
        return self.create_directory(term_path), term_path
    
    def create_school_timetable_academic_term_break_directory(self, timetable_path, term_name):
        """Create a directory for a specific term within an academic year."""
        term_path = os.path.join(timetable_path, "terms", "term_breaks", f"{term_name.replace(' ', '_')}")
        return self.create_directory(term_path), term_path

    def create_school_timetable_academic_week_directory(self, timetable_path, week_number):
        """Create a directory for a specific week within a term of a specific year."""
        week_path = os.path.join(timetable_path, "weeks", f"{week_number}")
        return self.create_directory(week_path), week_path

    def create_school_timetable_academic_day_directory(self, timetable_path, academic_day):
        """Create a directory for a specific day within a week of a term."""
        day_path = os.path.join(timetable_path, "days",f"{academic_day:02}")
        return self.create_directory(day_path), day_path
    
    def create_school_timetable_period_directory(self, timetable_path, academic_day, period_dir):
        """Create a directory for a specific period within a day."""
        period_path = os.path.join(timetable_path, "days",f"{academic_day:02}", f"{period_dir}")
        return self.create_directory(period_path), period_path
    
    def create_school_curriculum_directory(self, school_path=None):
        """Create a directory for the curriculum."""
        if school_path is None:
            curriculum_path = os.path.join(self.root_path, "curriculum")
        else:
            curriculum_path = os.path.join(school_path, "curriculum")

        return self.create_directory(curriculum_path), curriculum_path
    
    def create_school_pastoral_directory(self, school_path=None):
        """Create a directory for the pastoral."""
        if school_path is None:
            pastoral_path = os.path.join(self.root_path, "pastoral")
        else:
            pastoral_path = os.path.join(school_path, "pastoral")

        return self.create_directory(pastoral_path), pastoral_path
        
    def create_school_curriculum_key_stage_directory(self, curriculum_path, key_stage):
        """Create a directory for a specific key stage within the curriculum."""
        key_stage_path = os.path.join(curriculum_path, "key_stages", f"{key_stage}")
        return self.create_directory(key_stage_path), key_stage_path
    
    def create_school_curriculum_keystage_syllabus_directory(self, curriculum_path, key_stage, key_stage_syllabus):
        """Create a directory for a specific key stage syllabus."""
        key_stage_syllabus_path = os.path.join(curriculum_path, "key_stages", f"{key_stage}", "syllabus", f"{key_stage_syllabus}")
        return self.create_directory(key_stage_syllabus_path), key_stage_syllabus_path
    
    def create_school_curriculum_year_group_directory(self, curriculum_path, year_group):
        """Create a directory for a specific year group."""
        year_group_path = os.path.join(curriculum_path, "year_groups", f"{year_group}")
        return self.create_directory(year_group_path), year_group_path
    
    def create_school_curriculum_year_group_syllabus_directory(self, curriculum_path, year_group, year_group_syllabus):
        """Create a directory for a specific year group syllabus."""
        year_group_syllabus_path = os.path.join(curriculum_path, "year_groups", f"{year_group}", "syllabus", f"{year_group_syllabus}")
        return self.create_directory(year_group_syllabus_path), year_group_syllabus_path
    
    def create_school_curriculum_topic_directory(self, curriculum_path, year_group, year_group_syllabus, topic):
        """Create a directory for a specific topic."""
        topic_path = os.path.join(curriculum_path, "year_groups", f"{year_group}", "syllabus", f"{year_group_syllabus}", "topics", f"{topic}")
        return self.create_directory(topic_path), topic_path
    
    def create_school_curriculum_lesson_directory(self, curriculum_path, year_group, year_group_syllabus, topic, lesson):
        """Create a directory for a specific lesson."""
        lesson_path = os.path.join(curriculum_path, "year_groups", f"{year_group}", "syllabus", f"{year_group_syllabus}", "topics", f"{topic}", "lessons", f"{lesson}")
        return self.create_directory(lesson_path), lesson_path
    
    def create_school_curriculum_lesson_learning_statement_directory(self, curriculum_path, year_group, year_group_syllabus, topic, lesson, learning_statement):
        """Create a directory for a specific learning statement."""
        learning_statement_path = os.path.join(curriculum_path, "year_groups", f"{year_group}", "syllabus", f"{year_group_syllabus}", "topics", f"{topic}", "lessons", f"{lesson}", "learning_statements", f"{learning_statement}")
        return self.create_directory(learning_statement_path), learning_statement_path
    
    def create_teacher_timetable_directory(self, teacher_path):
        teacher_timetable_path = os.path.join(teacher_path, "timetable")
        return self.create_directory(teacher_timetable_path), teacher_timetable_path
    
    def create_teacher_class_directory(self, teacher_timetable_path, class_name):
        class_path = os.path.join(teacher_timetable_path, "classes", class_name)
        return self.create_directory(class_path), class_path

    def create_teacher_timetable_lesson_directory(self, class_path, lesson_id):
        lesson_path = os.path.join(class_path, "timetabled_lessons", lesson_id)
        return self.create_directory(lesson_path), lesson_path

    def create_teacher_planned_lesson_directory(self, class_path, lesson_id):
        planned_lesson_path = os.path.join(class_path, "planned_lessons", lesson_id)
        return self.create_directory(planned_lesson_path), planned_lesson_path
    
    # TLDraw File Creation
    def create_default_tldraw_file(self, node_path, node_data):
        """Create a tldraw file for a node."""
        logging.info(f"Creating tldraw file for node at {node_path}")
        
        # Ensure the directory exists
        os.makedirs(node_path, exist_ok=True)
        
        tldraw_path = os.path.join(node_path, 'tldraw_file.json')
        
        # Create default tldraw content
        tldraw_content = {
            "document": {
                "store": {
                    "document:document": {
                        "gridSize": 10,
                        "name": "",
                        "meta": {},
                        "id": "document:document",
                        "typeName": "document"
                    },
                    "page:page": {
                        "meta": {},
                        "id": "page:page",
                        "name": "Page 1",
                        "index": "a1",
                        "typeName": "page"
                    },
                },
                "schema": {
                    "schemaVersion": 2,
                    "sequences": {
                        "com.tldraw.store": 4,
                        "com.tldraw.asset": 1,
                        "com.tldraw.camera": 1,
                        "com.tldraw.document": 2,
                        "com.tldraw.instance": 25,
                        "com.tldraw.instance_page_state": 5,
                        "com.tldraw.page": 1,
                        "com.tldraw.instance_presence": 5,
                        "com.tldraw.pointer": 1,
                        "com.tldraw.shape": 4,
                        "com.tldraw.asset.bookmark": 2,
                        "com.tldraw.asset.image": 5,
                        "com.tldraw.asset.video": 5,
                        "com.tldraw.shape.group": 0,
                        "com.tldraw.shape.text": 2,
                        "com.tldraw.shape.bookmark": 2,
                        "com.tldraw.shape.draw": 2,
                        "com.tldraw.shape.geo": 9,
                        "com.tldraw.shape.note": 7,
                        "com.tldraw.shape.line": 5,
                        "com.tldraw.shape.frame": 0,
                        "com.tldraw.shape.arrow": 5,
                        "com.tldraw.shape.highlight": 1,
                        "com.tldraw.shape.embed": 4,
                        "com.tldraw.shape.image": 4,
                        "com.tldraw.shape.video": 2,
                        "com.tldraw.shape.microphone": 1,
                        "com.tldraw.shape.transcriptionText": 0,
                        "com.tldraw.binding.arrow": 0
                    }
                }
            },
            "session": {
                "version": 0,
                "currentPageId": "page:page",
                "pageStates": [{
                    "pageId": "page:page",
                    "camera": {"x": 0, "y": 0, "z": 1},
                    "selectedShapeIds": []
                }]
            },
            "node_data": node_data
        }
        
        with open(tldraw_path, 'w') as f:
            json.dump(tldraw_content, f, indent=4)
            
        logging.info(f"tldraw file created at {tldraw_path}")
        return tldraw_path