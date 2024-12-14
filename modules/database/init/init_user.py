from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_init_user'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from modules.database.tools import neo4j_session_tools
from modules.database.tools import neo4j_driver_tools
from modules.database.tools.neo4j_db_formatter import format_user_email_for_neo_db
import modules.database.schemas.entity_neo as entity_neo
import modules.database.init.init_calendar as init_calendar
import modules.database.schemas.relationships.entity_relationships as entity_relationships
import modules.database.tools.neontology_tools as neon
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from datetime import timedelta, datetime
import time
from abc import ABC, abstractmethod
import json

class UserCreator(ABC):
    def __init__(self, db_name, user_type, username, email, user_id):
        self.db_name = db_name
        self.user_type = user_type
        self.username = username
        self.email = email
        self.user_id = user_id
        self.fs_handler = ClassroomCopilotFilesystem(db_name, init_run_type="user")
        self.user_nodes = {'user_node': None}

    @abstractmethod
    def create_user(self):
        pass

    def create_user_node(self, user_path, db_name, worker_node):
        logging.info(f"Module is creating user node for {self.user_type} with user_path {user_path}")
        
        logging.info(f"Worker node: {worker_node}")
        
        logging.info(f"DB name: {db_name}")
        
        try:
            formatted_email = format_user_email_for_neo_db(self.email)
            user_node = entity_neo.UserNode(
                unique_id=f"User_{formatted_email}",
                user_id=self.user_id,
                user_type=self.user_type,
                user_name=self.username,
                user_email=self.email,
                worker_db_name=db_name,
                worker_node_data=json.dumps(worker_node.to_dict()),
                path=user_path
            )
            neon.create_or_merge_neontology_node(user_node, database=self.db_name, operation='merge')
            logging.info(f"User node created: {user_node}")
            # Create the tldraw file for the node
            self.fs_handler.create_default_tldraw_file(user_node.path, user_node.to_dict())
            return user_node
        except Exception as e:
            logging.error(f"Error creating user node: {e}")
            raise

    def create_tldraw_file_for_node(self, node, node_path):
        # TODO: This is a bit of a hack to get the node data, but it works for now.
        node_data = {
            "unique_id": node.unique_id,
            "type": node.__class__.__name__,
            "name": node.user_name if hasattr(node, 'user_name') else getattr(node, 'name', 'Unnamed Node')
        }
        return self.fs_handler.create_default_tldraw_file(node_path, node_data)

class SchoolUserCreator(UserCreator):
    def __init__(self, db_name, user_type, username, email, user_id, school_node, worker_data):
        
        super().__init__(db_name, user_type, username, email, user_id)
        
        self.school_node = school_node
        
        self.worker_data = json.loads(worker_data) if isinstance(worker_data, str) else worker_data
        

    def create_user(self):
        _, school_user_path = self.fs_handler.create_user_directory(self.user_type, self.username, school_path=self.school_node.path)
        
        if self.user_type in ['email_teacher', 'ms_teacher']:
            worker_node = self.create_teacher_node(school_user_path)
            self.create_tldraw_file_for_node(worker_node, school_user_path)
        elif self.user_type in ['email_student', 'ms_student']:
            worker_node = self.create_student_node(school_user_path)
            self.create_tldraw_file_for_node(worker_node, school_user_path)
        else:
            raise ValueError(f"User type {self.user_type} not supported")
        
        self.user_nodes[f'{self.user_type}_node'] = worker_node
        
        user_node = self.create_user_node(school_user_path, self.db_name, worker_node)
        
        logging.info(f"User node created: {user_node}")
        
        self.create_tldraw_file_for_node(user_node, school_user_path)
        
        self.user_nodes['user_node'] = user_node

        self.create_user_worker_relationship(user_node, worker_node)
        
        self.create_worker_school_relationship(worker_node, self.school_node)
        
        logging.info(f"Worker school relationship created between {worker_node} and {self.school_node}")
        return self.user_nodes

    def create_teacher_node(self, user_path):
        logging.debug(f"Teacher node will be created for school: {self.school_node}")
        try:
            teacher_node = entity_neo.TeacherNode(
                unique_id=f"Teacher_{self.user_id}",
                teacher_code=self.worker_data['teacher_code'],
                teacher_name_formal=self.worker_data['teacher_name_formal'],
                teacher_email=self.worker_data['teacher_email'],
                path=user_path
            )
            school_db = f"cc.ccschools.{self.school_node.school_uuid}"
            logging.warning(f"Teacher node template created: {teacher_node}.. setting school db to {school_db}")
            
            neon.create_or_merge_neontology_node(teacher_node, database=school_db, operation='merge')
            
            logging.info(f"Teacher node merged into database {school_db}: {teacher_node}")
            return teacher_node
        except KeyError as ke:
            raise ValueError(f"Missing required key in worker_data: {ke}")
        except Exception as e:
            raise ValueError(f"Error creating teacher node: {e}")

    def create_student_node(self, user_path):
        student_node = entity_neo.StudentNode(
            unique_id=f"Student_{self.user_id}",
            student_code=self.worker_data['student_code'],
            student_name_formal=self.worker_data['student_name_formal'],
            student_email=self.worker_data['student_email'],
            path=user_path
        )
        neon.create_or_merge_neontology_node(student_node, database=self.db_name, operation='merge')
        logging.info(f"Student node created: {student_node}")
        return student_node

    def create_user_worker_relationship(self, user_node, worker_node):
        user_role_rel = entity_relationships.UserIsWorker(source=user_node, target=worker_node)
        neon.create_or_merge_neontology_relationship(user_role_rel, database=self.db_name, operation='merge')
        logging.info(f"Relationship created between user and worker")

    def create_worker_school_relationship(self, worker_node, school_node):
        worker_school_rel = entity_relationships.EntityBelongsToSchool(source=worker_node, target=school_node)
        neon.create_or_merge_neontology_node(worker_school_rel, database=self.db_name, operation='merge')
        logging.info(f"Relationship created between worker and school")

class NonSchoolUserCreator(UserCreator):
    def create_user(self):
        _, user_path = self.fs_handler.create_user_directory(self.user_type, self.username)
        _, developer_node_path = self.fs_handler.create_user_directory(self.user_type, self.username)

        if self.user_type == 'cc_admin':
            cc_admin_node = self.create_developer_node(user_path)
        elif self.user_type == 'developer':
            developer_node = self.create_developer_node(user_path)
        else:
            raise ValueError(f"User type {self.user_type} not supported")
        
        self.user_nodes[f'{self.user_type}_node'] = developer_node
        
        user_node = self.create_user_node(user_path, self.db_name, developer_node)
        
        self.create_tldraw_file_for_node(user_node, user_path)
        
        self.user_nodes['user_node'] = user_node
        
        self.user_nodes[f'{self.user_type}_node'] = developer_node
        
        self.create_user_specific_relationship(user_node, developer_node)
        
        calendar_nodes = self.create_calendar(developer_node)
        
        self.user_nodes['calendar_nodes'] = calendar_nodes

        return self.user_nodes

    def create_developer_node(self, user_path):
        try:
            developer_node = entity_neo.DeveloperNode(
                unique_id=f"DeveloperNode_{self.user_id}",
                user_name=self.username,
                user_email=self.email,
                path=user_path
            )
            developer_db_name = f"cc.ccusers.{format_user_email_for_neo_db(self.email)}"
            logging.warning(f"Developer node template created: {developer_node}.. setting db to {developer_db_name}")
            
            neon.create_or_merge_neontology_node(developer_node, database=developer_db_name, operation='merge')
            
            logging.info(f"Developer node created: {developer_node}")
            return developer_node
        except Exception as e:
            raise ValueError(f"Error creating developer node: {e}")

    def create_user_specific_relationship(self, user_node, specific_node):
        specific_user_rel = entity_relationships.UserIsStandardUser(source=user_node, target=specific_node)
        neon.create_or_merge_neontology_relationship(specific_user_rel, database=self.db_name, operation='merge')
        logging.info(f"Relationship created between user and specific node")

    def create_calendar(self, entity_node):
        start_date = datetime.now().date()
        end_date = (datetime.now() + timedelta(days=5)).date()
        calendar_nodes = init_calendar.create_calendar(self.db_name, start_date, end_date, attach_to_calendar_node=True, entity_node=entity_node)
        
        logging.warning(f"Calendar nodes created: {calendar_nodes}")
        return calendar_nodes

def create_user(db_name, user_type, username, email, user_id, school_node=None, worker_data=None):
    """Create user nodes and databases"""
    logging.info(f"[1.0] Starting user creation process")
    logging.info(f"[1.1] Input parameters: type={user_type}, email={email}, username={username}")
    
    # 1. Format email and create user's private database
    formatted_email = format_user_email_for_neo_db(email)
    user_db_name = f"cc.ccusers.{formatted_email}"
    logging.info(f"[1.2] Formatted database name: {user_db_name}")
    
    try:
        with neo4j_driver_tools.get_driver().session() as session:
            logging.info(f"[2.0] Creating user's private database")
            neo4j_session_tools.create_database(session, user_db_name)
            logging.info(f"[2.1] Successfully created database: {user_db_name}")
    except Exception as e:
        logging.error(f"[2.X] Error creating user database: {str(e)}")
        raise
        
    # 2. Initialize Neontology connection
    logging.info(f"[3.0] Initializing Neontology connection")
    neon.init_neontology_connection()
    
    # 3. Create filesystem structure for user's private database
    logging.info(f"[4.0] Setting up filesystem structure")
    private_fs_handler = ClassroomCopilotFilesystem(user_db_name, init_run_type="user")
    _, user_private_path = private_fs_handler.create_user_directory(username)
    logging.info(f"[4.1] Created user directory at: {user_private_path}")
    
    # 4. Create worker node in both DBs if school-related user
    if user_type in ['email_teacher', 'ms_teacher', 'email_student', 'ms_student']:
        logging.info(f"[5.0] Creating school-related worker nodes")
        if not school_node:
            logging.error(f"[5.X] School node required but not provided")
            raise ValueError("School node required for school-related user types")
            
        # Create worker node for school database
        school_db = f"cc.ccschools.{school_node.school_uuid}"
        logging.info(f"[5.1] Setting up school database: {school_db}")
        school_fs_handler = ClassroomCopilotFilesystem(school_db, init_run_type="school")
        _, school_worker_path = school_fs_handler.create_user_directory(
            username=username,
            user_type=user_type,
            school_path=school_node.path
        )
        logging.info(f"[5.2] Created school worker directory at: {school_worker_path}")
        
        # Create worker node for private database with correct path
        worker_code = worker_data.get('teacher_code' if 'teacher' in user_type else 'student_code')
        _, private_worker_path = private_fs_handler.create_user_worker_directory(
            user_path=user_private_path,
            worker_code=worker_code
        )
        
        # Create worker nodes
        if user_type in ['email_teacher', 'ms_teacher']:
            logging.info(f"[6.0] Creating teacher worker nodes")
            # School DB worker node
            school_worker_node = create_teacher_node(
                school_db, user_id, username, email, 
                school_worker_path, worker_data, school_node
            )
            logging.info(f"[6.1] Created school teacher node: {school_worker_node.unique_id}")
            school_fs_handler.create_default_tldraw_file(school_worker_path, school_worker_node.to_dict())
            logging.info(f"[6.2] Created school tldraw file")
            
            # Private DB worker node (copy of school worker node but with private path)
            private_worker_node = create_teacher_node(
                user_db_name, user_id, username, email, 
                private_worker_path, worker_data, school_node
            )
            logging.info(f"[6.3] Created private teacher node: {private_worker_node.unique_id}")
            private_fs_handler.create_default_tldraw_file(private_worker_path, private_worker_node.to_dict())
            logging.info(f"[6.4] Created private tldraw file")
        else:
            logging.info(f"[6.0] Creating student worker nodes")
            # School DB worker node
            school_worker_node = create_student_node(
                school_db, user_id, username, email, 
                school_worker_path, worker_data, school_node
            )
            logging.info(f"[6.1] Created school student node: {school_worker_node.unique_id}")
            school_fs_handler.create_default_tldraw_file(school_worker_path, school_worker_node.to_dict())
            logging.info(f"[6.2] Created school tldraw file")
            
            # Private DB worker node
            private_worker_node = create_student_node(
                user_db_name, user_id, username, email, 
                private_worker_path, worker_data, school_node
            )
            logging.info(f"[6.3] Created private student node: {private_worker_node.unique_id}")
            private_fs_handler.create_default_tldraw_file(private_worker_path, private_worker_node.to_dict())
            logging.info(f"[6.4] Created private tldraw file")
        
        # Create relationships in school DB
        logging.info(f"[7.0] Creating school relationships")
        neon.create_or_merge_neontology_relationship(
            entity_relationships.EntityBelongsToSchool(
                source=school_worker_node, 
                target=school_node
            ),
            database=school_db,
            operation='merge'
        )
        logging.info(f"[7.1] Created school relationship")
        
        # Use private worker node for user node creation
        worker_node = private_worker_node
    else:
        logging.info(f"[5.0] Non-school user type, skipping worker node creation")
        worker_node = None
    
    # 5. Create user node with worker data in private DB
    logging.info(f"[8.0] Creating main user node")
    user_node = entity_neo.UserNode(
        unique_id=f"User_{formatted_email}",
        user_id=user_id,
        user_type=user_type,
        user_name=username,
        user_email=email,
        path=user_private_path,
        worker_node_data=json.dumps(worker_node.to_dict()) if worker_node else None
    )
    neon.create_or_merge_neontology_node(user_node, database=user_db_name, operation='merge')
    logging.info(f"[8.1] Created user node: {user_node.unique_id}")
    
    # Create tldraw file for user node
    private_fs_handler.create_default_tldraw_file(user_private_path, user_node.to_dict())
    logging.info(f"[8.2] Created user tldraw file")
    
    # 6. Create relationship between user and worker in private DB
    if worker_node:
        logging.info(f"[9.0] Creating user-worker relationship")
        neon.create_or_merge_neontology_relationship(
            entity_relationships.UserIsWorker(source=user_node, target=worker_node),
            database=user_db_name,
            operation='merge'
        )
        logging.info(f"[9.1] Created user-worker relationship")
    
    # 7. Create calendar for user
    try:
        logging.info(f"[10.0] Creating user calendar")
        calendar_nodes = init_calendar.create_calendar(
            user_db_name,
            datetime.now().date(),
            (datetime.now() + timedelta(days=30)).date(),
            attach_to_calendar_node=True,
            entity_node=user_node
        )
        
        ## Create tldraw files for calendar nodes
        #logging.info(f"[10.1] Creating calendar tldraw files")
        #for node_type, nodes in calendar_nodes.items():
        #    if isinstance(nodes, list):
        #        for node in nodes:
        #            private_fs_handler.create_default_tldraw_file(node.path, node.to_dict())
        #    elif nodes:  # Single node
        #        private_fs_handler.create_default_tldraw_file(nodes.path, nodes.to_dict())
        
        # Convert calendar nodes to dictionaries for response
        logging.info(f"[10.2] Preparing calendar response")
        serialized_calendar = {
            'calendar_node': calendar_nodes['calendar_node'].to_dict() if calendar_nodes.get('calendar_node') else None,
            'calendar_year_nodes': [node.to_dict() for node in calendar_nodes.get('calendar_year_nodes', [])],
            'calendar_month_nodes': [node.to_dict() for node in calendar_nodes.get('calendar_month_nodes', [])],
            'calendar_week_nodes': [node.to_dict() for node in calendar_nodes.get('calendar_week_nodes', [])],
            'calendar_day_nodes': [node.to_dict() for node in calendar_nodes.get('calendar_day_nodes', [])]
        }
        
        logging.info(f"[11.0] User creation process complete")
        return {
            'user_node': user_node.to_dict(),
            'worker_node': worker_node.to_dict() if worker_node else None,
            'calendar_nodes': serialized_calendar
        }
        
    except Exception as e:
        logging.error(f"[10.X] Error creating calendar: {str(e)}")
        logging.info(f"[11.0] User creation complete with calendar error")
        return {
            'user_node': user_node.to_dict(),
            'worker_node': worker_node.to_dict() if worker_node else None,
            'calendar_nodes': None
        }

def create_teacher_node(db_name, user_id, username, email, path, worker_data, school_node):
    """Create teacher worker node"""
    if not worker_data or not isinstance(worker_data, dict):
        worker_data = {
            'teacher_code': username,
            'teacher_name_formal': username,
            'teacher_email': email
        }
        
    # Add worker_db_name based on school
    worker_db_name = f"cc.ccschools.{school_node.school_uuid}"
        
    teacher_node = entity_neo.TeacherNode(
        unique_id=f"Teacher_{user_id}",
        teacher_code=worker_data['teacher_code'],
        teacher_name_formal=worker_data['teacher_name_formal'],
        teacher_email=worker_data['teacher_email'],
        path=path,
        worker_db_name=worker_db_name
    )
    neon.create_or_merge_neontology_node(teacher_node, database=db_name, operation='merge')
    return teacher_node

def create_student_node(db_name, user_id, username, email, path, worker_data, school_node):
    """Create student worker node"""
    if not worker_data or not isinstance(worker_data, dict):
        worker_data = {
            'student_code': username,
            'student_name_formal': username,
            'student_email': email
        }
        
    # Add worker_db_name based on school
    worker_db_name = f"cc.ccschools.{school_node.school_uuid}"
        
    student_node = entity_neo.StudentNode(
        unique_id=f"Student_{user_id}",
        student_code=worker_data['student_code'],
        student_name_formal=worker_data['student_name_formal'],
        student_email=worker_data['student_email'],
        path=path,
        worker_db_name=worker_db_name
    )
    neon.create_or_merge_neontology_node(student_node, database=db_name, operation='merge')
    return student_node