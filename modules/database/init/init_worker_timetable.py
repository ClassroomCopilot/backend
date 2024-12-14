from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_init_init_worker_timetable'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import pandas as pd
import re
import modules.database.tools.neo4j_driver_tools as driver
import modules.database.tools.neontology_tools as neon
import modules.database.tools.neo4j_session_tools as session
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from modules.database.schemas.entity_neo import SubjectClassNode, TeacherNode
from modules.database.schemas.timetable_neo import AcademicPeriodNode, RegistrationPeriodNode, BreakPeriodNode, OffTimetablePeriodNode
from modules.database.schemas.teacher_timetable_neo import TeacherTimetableNode, TimetableLessonNode, PlannedLessonNode
from modules.database.schemas.curriculum_neo import YearGroupSyllabusNode
from modules.database.schemas.relationships.planning_relationships import TimetableLessonBelongsToPeriod, TimetableLessonHasPlannedLesson, TeacherHasTimetable, TimetableHasClass, ClassHasLesson, TimetableLessonFollowsTimetableLesson, PlannedLessonFollowsPlannedLesson, SubjectClassBelongsToYearGroupSyllabus

def init_worker_timetable(timetable_df: pd.DataFrame, school_worker_node: TeacherNode):
    logging.info(f"School worker node: {school_worker_node}")
    worker_node = TeacherNode(**school_worker_node)
    logging.info(f"Worker node: {worker_node}")
    worker_db_name = worker_node.worker_db_name
    
    logging.info(f"Initialising filesystem handler...")
    fs_handler = ClassroomCopilotFilesystem(db_name=worker_db_name, init_run_type="user")
    _, worker_timetable_path = fs_handler.create_teacher_timetable_directory(worker_node.path)
    
    logging.info(f"Initialising neo4j connection...")
    neon.init_neontology_connection()
    
    try:
        timetable_unique_id = f"TeacherTimetable_{worker_node.teacher_code}"
        worker_timetable = TeacherTimetableNode(
            unique_id=timetable_unique_id,
            path=worker_timetable_path
        )
        neon.create_or_merge_neontology_node(worker_timetable, database=worker_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(worker_timetable.path, worker_timetable.to_dict())
        neon.create_or_merge_neontology_relationship(
            TeacherHasTimetable(source=worker_node, target=worker_timetable),
            database=worker_db_name, operation='merge'
        )
        logging.info(f"Teacher timetable node created: {worker_timetable}")
        
        # Group the timetable by class
        class_groups = timetable_df.groupby('Class')
        for class_name, class_df in class_groups:
            if pd.notna(class_name):
                class_name_safe = re.sub(r'[^A-Za-z0-9_ ]+', '', class_name)
                _, class_path = fs_handler.create_teacher_class_directory(worker_timetable.path, class_name_safe)
                
                subject_class_node_unique_id = f"SubjectClass_{class_name}"
                subject_class_node = SubjectClassNode(
                    unique_id=subject_class_node_unique_id,
                    subject_class_code=class_name,
                    year_group=str(int(class_df['YearGroup'].iloc[0])), # TODO: Hacky fix for the year group being a float
                    subject=str(class_df['Subject'].iloc[0]),
                    subject_code=str(class_df['SubjectCode'].iloc[0]),
                    path=class_path
                )
                neon.create_or_merge_neontology_node(subject_class_node, database=worker_db_name, operation='merge')
                logging.info(f"Class node created: {subject_class_node}")
                # Create the tldraw file for the node
                fs_handler.create_default_tldraw_file(subject_class_node.path, subject_class_node.to_dict())
                
                # Link ClassNode to TeacherTimetableNode
                neon.create_or_merge_neontology_relationship(
                    TimetableHasClass(source=worker_timetable, target=subject_class_node),
                    database=worker_db_name, operation='merge'
                )
                logging.info(f"Relationship created from {worker_timetable.unique_id} to {subject_class_node.unique_id}")
                
                # Link class to corresponding YearGoupSyllabus
                
                year_group_syllabus_search_driver = driver.get_driver(worker_db_name)
                year_group_syllabus_search_session = year_group_syllabus_search_driver.session(database=worker_db_name)
                year_group_syllabus = session.find_nodes_by_label_and_properties(year_group_syllabus_search_session, "YearGroupSyllabus", {"yr_syllabus_year_group": subject_class_node.year_group, "yr_syllabus_subject_code": subject_class_node.subject_code})
                if year_group_syllabus:
                    year_group_syllabus_node_data = year_group_syllabus[0]
                    year_group_syllabus_node = YearGroupSyllabusNode(**year_group_syllabus_node_data)
                    neon.create_or_merge_neontology_relationship(
                        SubjectClassBelongsToYearGroupSyllabus(source=subject_class_node, target=year_group_syllabus_node),
                        database=worker_db_name, operation='merge'
                    )
                    logging.info(f"Relationship created from {subject_class_node.unique_id} to {year_group_syllabus_node.unique_id}")
                else:
                    logging.warning(f"No YearGroupSyllabus found for class {class_name} with year group {subject_class_node.year_group} and subject code {subject_class_node.subject_code}")
                
                class_lesson_nodes = []
                planned_lesson_nodes = []
                lesson_number = 0
                for _, row in class_df.iterrows():
                    properties = {
                        "period_code": row['PeriodCode']
                    }
                    class_lessons_search_driver = driver.get_driver(worker_db_name)
                    class_lessons_search_session = class_lessons_search_driver.session(database=worker_db_name)
                    # If the period code contains "Rg" then we want to find the corresponding registration period and use its unique id
                    if "Rg" in row['PeriodCode']: # TODO: This is hacky and not very flexible. We are assuming that any period code containing "Rg" is a registration period. We should probably find a more robust way to identify registration periods
                        logging.info(f"Registration period found for class {class_name} with period code {row['PeriodCode']}")
                        class_lessons = session.find_nodes_by_label_and_properties(class_lessons_search_session, "RegistrationPeriod", properties)
                    else:
                        logging.info(f"Academic period found for class {class_name} with period code {row['PeriodCode']}")
                        class_lessons = session.find_nodes_by_label_and_properties(class_lessons_search_session, "AcademicPeriod", properties)
                    if class_lessons:
                        lesson_of_same_period = 0
                        number_of_lessons = len(class_lessons)
                        while lesson_of_same_period < number_of_lessons:
                            class_lesson = class_lessons[lesson_of_same_period]
                            if "Rg" in row['PeriodCode']:
                                period_node = RegistrationPeriodNode(**class_lesson)
                            else:
                                period_node = AcademicPeriodNode(**class_lesson)
                            lesson_period_code = row['PeriodCode']
                            date = class_lesson['date']
                            date_safe = date.strftime("%Y-%m-%d")
                            # Clean the class_name to make it directory-safe (catch all for invalid characters)
                            timetable_lesson_unique_id = f"TimetableLesson_{timetable_unique_id}_Class_{class_name}_Lesson_{lesson_number}_{date_safe}_{lesson_period_code}"
                            
                            timetable_lesson_node = TimetableLessonNode(
                                unique_id=timetable_lesson_unique_id,
                                subject_class=class_name,
                                date=date,
                                start_time=class_lesson['start_time'].time(), # TODO: This is probably how we should format the start and end time properties for all such nodes
                                end_time=class_lesson['end_time'].time(),
                                period_code=lesson_period_code,
                                path="Not set"
                            )
                            neon.create_or_merge_neontology_node(timetable_lesson_node, database=worker_db_name, operation='merge')
                            logging.info(f"TimetableLessonNode created: {timetable_lesson_node}")
                            class_lesson_nodes.append(timetable_lesson_node)
                            
                            neon.create_or_merge_neontology_relationship(
                                TimetableLessonBelongsToPeriod(source=timetable_lesson_node, target=period_node),
                                database=worker_db_name, operation='merge'
                            )
                            logging.info(f"Relationship created from {timetable_lesson_node.unique_id} to {period_node.unique_id}")
                            
                            # Link TimetableLessonNode to ClassNode
                            neon.create_or_merge_neontology_relationship(
                                ClassHasLesson(source=subject_class_node, target=timetable_lesson_node),
                                database=worker_db_name, operation='merge'
                            )
                            logging.info(f"Relationship created from {subject_class_node.unique_id} to {timetable_lesson_node.unique_id}")
                            
                            # Create PlannedLessonNode
                            planned_lesson_unique_id = f"PlannedLesson_{timetable_unique_id}_Class_{class_name}_Lesson_{lesson_number}_{date_safe}_{lesson_period_code}"
                            planned_lesson_node = PlannedLessonNode(
                                unique_id=planned_lesson_unique_id,
                                date=date,
                                start_time=class_lesson['start_time'].time(),
                                end_time=class_lesson['end_time'].time(),
                                period_code=lesson_period_code,
                                subject_class=class_name,
                                year_group=subject_class_node.year_group,
                                subject=subject_class_node.subject,
                                teacher_code=worker_node.teacher_code,
                                planning_status="Unplanned",
                                topic_code=None,
                                topic_name=None,
                                lesson_code=None,
                                lesson_name=None,
                                learning_statement_codes=None,
                                learning_statements=None,
                                learning_resource_codes=None,
                                learning_resources=None,
                                path="Not set"
                            )
                            # Create the PlannedLessonNode
                            neon.create_or_merge_neontology_node(planned_lesson_node, database=worker_db_name, operation='merge')
                            logging.info(f"PlannedLessonNode created: {planned_lesson_node}")
                            planned_lesson_nodes.append(planned_lesson_node)
                            
                            # Link PlannedLessonNode to TimetableLessonNode
                            neon.create_or_merge_neontology_relationship(
                                TimetableLessonHasPlannedLesson(source=timetable_lesson_node, target=planned_lesson_node),
                                database=worker_db_name, operation='merge'
                            )
                            logging.info(f"Relationship created from {timetable_lesson_node.unique_id} to {planned_lesson_node.unique_id}")
                            lesson_of_same_period += 1
                            lesson_number += 1
                    else:
                        logging.warning(f"No class periods found for class {class_name} on day {row['DayOfWeek']}")
                # Sort the nodes by date and start time
                class_lesson_nodes.sort(key=lambda x: (x.date, x.start_time))
                planned_lesson_nodes.sort(key=lambda x: (x.date, x.start_time))
                
                # Create sequential relationships and directories for TimetableLessonNodes
                for i in range(1, len(class_lesson_nodes)):
                    previous_node = class_lesson_nodes[i - 1]
                    current_node = class_lesson_nodes[i]
                    i_safe = f"{i:02d}"
                    _, class_lesson_path = fs_handler.create_teacher_timetable_lesson_directory(class_path, f"{i_safe}_{current_node.date}_{current_node.period_code}")
                    current_node.path = class_lesson_path
                    neon.create_or_merge_neontology_node(current_node, database=worker_db_name, operation='merge')
                    logging.info(f"TimetableLessonNode directory created and node merged into database: {current_node}")
                    # Create the tldraw file for the node
                    fs_handler.create_default_tldraw_file(current_node.path, current_node.to_dict())
                    if previous_node:
                        neon.create_or_merge_neontology_relationship(
                            TimetableLessonFollowsTimetableLesson(source=previous_node, target=current_node),
                            database=worker_db_name, operation='merge'
                        )
                        logging.info(f"Sequential relationship created between {previous_node.unique_id} and {current_node.unique_id}")
                
                # Create sequential relationships for PlannedLessonNodes
                for i in range(1, len(planned_lesson_nodes)):
                    previous_node = planned_lesson_nodes[i - 1]
                    current_node = planned_lesson_nodes[i]
                    i_safe = f"{i:02d}"
                    _, planned_lesson_path = fs_handler.create_teacher_planned_lesson_directory(class_path, f"{i_safe}_{current_node.date}_{current_node.period_code}")
                    current_node.path = planned_lesson_path
                    neon.create_or_merge_neontology_node(current_node, database=worker_db_name, operation='merge')
                    logging.info(f"PlannedLessonNode directory created and node merged into database: {current_node}")
                    # Create the tldraw file for the node
                    fs_handler.create_default_tldraw_file(current_node.path, current_node.to_dict())
                    if previous_node:
                        neon.create_or_merge_neontology_relationship(
                            PlannedLessonFollowsPlannedLesson(source=previous_node, target=current_node),
                        database=worker_db_name, operation='merge'
                    )
                    logging.info(f"Sequential relationship created between {previous_node.unique_id} and {current_node.unique_id}")
        logging.info(f"Successfully initialized worker timetable for worker {worker_node.teacher_code}")
        return {"status": "success", "message": "Worker timetable initialized successfully"}
    
    except Exception as e:
        logging.error(f"Error initializing worker timetable: {str(e)}")
        return {"status": "error", "message": f"Error initializing worker timetable: {str(e)}"}



