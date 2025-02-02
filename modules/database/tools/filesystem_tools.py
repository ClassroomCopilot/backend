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
    
    def create_school_department_directory(self, school_path, department):
        """Create a directory for a specific department within the school."""
        department_path = os.path.join(school_path, "departments", f"{department}")
        return self.create_directory(department_path), department_path
    
    def create_department_subject_directory(self, department_path, subject_name):
        """Create a directory for a specific subject within a department."""
        subject_path = os.path.join(department_path, "subjects", f"{subject_name}")
        return self.create_directory(subject_path), subject_path
        
    def create_curriculum_key_stage_syllabus_directory(self, curriculum_path, key_stage, subject_name, syllabus_id):
        """Create a directory for a specific key stage syllabus under the curriculum structure."""
        # Replace spaces with underscores and remove any special characters from subject name
        safe_subject_name = re.sub(r'[^\w\-_\.]', '_', subject_name)
        syllabus_path = os.path.join(curriculum_path, "subjects", safe_subject_name, "key_stage_syllabuses", f"KS{key_stage}", f"KS{key_stage}.{safe_subject_name}")
        return self.create_directory(syllabus_path), syllabus_path

    def create_pastoral_year_group_directory(self, pastoral_path, year_group):
        """Create a directory for a specific year group under the pastoral structure."""
        year_group_path = os.path.join(pastoral_path, "year_groups", f"Y{year_group}")
        return self.create_directory(year_group_path), year_group_path
        
    def create_curriculum_year_group_syllabus_directory(self, curriculum_path, subject_name, year_group, syllabus_id):
        """Create a directory for a specific year group syllabus under the curriculum structure."""
        # Replace spaces with underscores and remove any special characters from subject name
        safe_subject_name = re.sub(r'[^\w\-_\.]', '_', subject_name)
        syllabus_path = os.path.join(curriculum_path, "subjects", safe_subject_name, "year_group_syllabuses", f"Y{year_group}", f"Y{year_group}.{safe_subject_name}")
        return self.create_directory(syllabus_path), syllabus_path
        
    def create_curriculum_topic_directory(self, year_group_syllabus_path, topic_id):
        """Create a directory for a specific topic under a year group syllabus."""
        topic_path = os.path.join(year_group_syllabus_path, "topics", f"{topic_id}")
        return self.create_directory(topic_path), topic_path
        
    def create_curriculum_lesson_directory(self, topic_path, lesson_id):
        """Create a directory for a specific lesson under a topic."""
        lesson_path = os.path.join(topic_path, "lessons", f"{lesson_id}")
        return self.create_directory(lesson_path), lesson_path
        
    def create_curriculum_learning_statement_directory(self, lesson_path, statement_id):
        """Create a directory for a specific learning statement under a lesson."""
        statement_path = os.path.join(lesson_path, "learning_statements", f"{statement_id}")
        return self.create_directory(statement_path), statement_path

    # Remove or mark as deprecated the old methods


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
                        }
                },
                "schema":
                    {"schemaVersion":2,
                    "sequences": {
                        "com.tldraw.store":4,
                        "com.tldraw.asset":1,
                        "com.tldraw.camera":1,
                        "com.tldraw.document":2,
                        "com.tldraw.instance":25,
                        "com.tldraw.instance_page_state":5,
                        "com.tldraw.page":1,
                        "com.tldraw.instance_presence":5,
                        "com.tldraw.pointer":1,
                        "com.tldraw.shape":4,
                        "com.tldraw.asset.bookmark":2,
                        "com.tldraw.asset.image":5,
                        "com.tldraw.asset.video":5,
                        "com.tldraw.shape.arrow":5,
                        "com.tldraw.shape.bookmark":2,
                        "com.tldraw.shape.draw":2,
                        "com.tldraw.shape.embed":4,
                        "com.tldraw.shape.frame":0,
                        "com.tldraw.shape.geo":9,
                        "com.tldraw.shape.group":0,
                        "com.tldraw.shape.highlight":1,
                        "com.tldraw.shape.image":4,
                        "com.tldraw.shape.line":5,
                        "com.tldraw.shape.note":8,
                        "com.tldraw.shape.text":2,
                        "com.tldraw.shape.video":2,
                        "com.tldraw.shape.youtube-embed":0,
                        "com.tldraw.shape.calendar":0,
                        "com.tldraw.shape.microphone":1,
                        "com.tldraw.shape.transcriptionText":0,
                        "com.tldraw.shape.slide":0,"com.tldraw.shape.slideshow":0,
                        "com.tldraw.shape.user_node":1,
                        "com.tldraw.shape.developer_node":1,
                        "com.tldraw.shape.student_node":1,
                        "com.tldraw.shape.teacher_node":1,
                        "com.tldraw.shape.calendar_node":1,
                        "com.tldraw.shape.calendar_year_node":1,
                        "com.tldraw.shape.calendar_month_node":1,
                        "com.tldraw.shape.calendar_week_node":1,
                        "com.tldraw.shape.calendar_day_node":1,
                        "com.tldraw.shape.calendar_time_chunk_node":1,
                        "com.tldraw.shape.teacher_timetable_node":1,
                        "com.tldraw.shape.timetable_lesson_node":1,
                        "com.tldraw.shape.planned_lesson_node":1,
                        "com.tldraw.shape.pastoral_structure_node":1,
                        "com.tldraw.shape.year_group_node":1,
                        "com.tldraw.shape.curriculum_structure_node":1,
                        "com.tldraw.shape.key_stage_node":1,
                        "com.tldraw.shape.key_stage_syllabus_node":1,
                        "com.tldraw.shape.year_group_syllabus_node":1,
                        "com.tldraw.shape.subject_node":1,
                        "com.tldraw.shape.topic_node":1,
                        "com.tldraw.shape.topic_lesson_node":1,
                        "com.tldraw.shape.learning_statement_node":1,
                        "com.tldraw.shape.science_lab_node":1,
                        "com.tldraw.shape.school_timetable_node":1,
                        "com.tldraw.shape.academic_year_node":1,
                        "com.tldraw.shape.academic_term_node":1,
                        "com.tldraw.shape.academic_week_node":1,
                        "com.tldraw.shape.academic_day_node":1,
                        "com.tldraw.shape.academic_period_node":1,
                        "com.tldraw.shape.registration_period_node":1,
                        "com.tldraw.shape.school_node":1,
                        "com.tldraw.shape.department_node":1,
                        "com.tldraw.shape.room_node":1,
                        "com.tldraw.shape.subject_class_node":1,
                        "com.tldraw.shape.general_relationship":1,
                        "com.tldraw.binding.arrow":0,
                        "com.tldraw.binding.slide-layout":0
                    }
                },
                "recordVersions": {
                    "asset": { "version": 1, "subTypeKey": "type", "subTypeVersions": {} },
                    "camera": { "version": 1 },
                    "document": { "version": 2 },
                    "instance": { "version": 21 },
                    "instance_page_state": { "version": 5 },
                    "page": { "version": 1 },
                    "shape": { "version": 3, "subTypeKey": "type", "subTypeVersions": {} },
                    "instance_presence": { "version": 5 },
                    "pointer": { "version": 1 }
                },
                "rootShapeIds":[],
                "bindings":[],
                "assets":[]
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