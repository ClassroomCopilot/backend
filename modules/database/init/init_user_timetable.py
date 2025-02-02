from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_init_init_user_timetable'
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
import modules.database.tools.neontology_tools as neon
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
from modules.database.schemas.entity_neo import UserNode, TeacherNode, SubjectClassNode
from modules.database.schemas.calendar_neo import CalendarDayNode
from modules.database.schemas.teacher_timetable_neo import (
    UserTeacherTimetableNode, UserTimetableLessonNode, PlannedLessonNode
)
from modules.database.schemas.relationships.entity_timetable_rels import (
    EntityHasTimetable
)
from modules.database.schemas.relationships.planning_relationships import (
    TeacherHasTimetable, TimetableHasClass, ClassHasLesson,
    TimetableLessonHasPlannedLesson
)
from modules.database.schemas.relationships.calendar_timetable_rels import (
    CalendarDayHasTimetableLesson, TimetableLessonBelongsToCalendarDay,
    CalendarDayHasPlannedLesson, PlannedLessonBelongsToCalendarDay
)

def get_school_worker_classes(school_db_name: str, user_unique_id: str, worker_unique_id: str) -> list:
    """
    Retrieve all classes for a worker from the school database.
    """
    query = """
    MATCH (w:Teacher {unique_id: $worker_id})-[:TEACHER_HAS_TIMETABLE]->(tt:TeacherTimetable)
    -[:TIMETABLE_HAS_CLASS]->(c:SubjectClass)
    RETURN c
    """
    with driver.get_driver(db_name=school_db_name).session(database=school_db_name) as session:
        result = session.run(query, worker_id=worker_unique_id)
        classes = [record['c'] for record in result]
        if not classes:
            logging.warning(f"No classes found for teacher {worker_unique_id} in school database")
        return classes

def get_school_class_periods(school_db_name: str, class_unique_id: str) -> list:
    """
    Retrieve all periods for a class from the school database.
    """
    query = """
    MATCH (c:SubjectClass {unique_id: $class_id})-[:CLASS_HAS_LESSON]->(l:TimetableLesson)
    RETURN l
    """
    with driver.get_driver(db_name=school_db_name).session(database=school_db_name) as session:
        result = session.run(query, class_id=class_unique_id)
        periods = [record['l'] for record in result]
        if not periods:
            logging.warning(f"No periods found for class {class_unique_id} in school database")
        return periods

def get_user_calendar_nodes(user_db_name: str, user_node: UserNode) -> list:
    """
    Retrieve all calendar day nodes for a user.
    """
    # First try to find any calendar days to verify the structure
    verify_query = """
    MATCH (w:User {unique_id: $user_id})
    OPTIONAL MATCH (w)-[:HAS_CALENDAR]->(c:Calendar)
    OPTIONAL MATCH (c)-[:CALENDAR_INCLUDES_YEAR]->(y:CalendarYear)
    OPTIONAL MATCH (y)-[:YEAR_INCLUDES_MONTH]->(m:CalendarMonth)
    OPTIONAL MATCH (m)-[:MONTH_INCLUDES_DAY]->(d:CalendarDay)
    RETURN w.unique_id as user_id, 
           count(c) as calendar_count,
           count(y) as year_count,
           count(m) as month_count,
           count(d) as day_count,
           collect(DISTINCT y.year) as years
    LIMIT 1
    """

    with driver.get_driver(db_name=user_db_name).session(database=user_db_name) as session:
        # First check the calendar structure
        result = session.run(verify_query, user_id=user_node.unique_id)
        if stats := result.single():
            logging.info(f"Calendar structure for user {stats['user_id']}: "
                        f"calendars={stats['calendar_count']}, "
                        f"years={stats['year_count']}, "
                        f"months={stats['month_count']}, "
                        f"days={stats['day_count']}, "
                        f"available years={stats['years']}")

            if stats['calendar_count'] == 0:
                logging.error(f"No calendar found for user {user_node.unique_id}")
                return []
            if stats['year_count'] == 0:
                logging.error(f"No calendar years found for user {user_node.unique_id}")
                return []
            if stats['month_count'] == 0:
                logging.error(f"No calendar months found for user {user_node.unique_id}")
                return []
            if stats['day_count'] == 0:
                logging.error(f"No calendar days found for user {user_node.unique_id}")
                return []

        # Get all calendar days without year filter
        query = """
        MATCH (w:User {unique_id: $user_id})-[:HAS_CALENDAR]->(c:Calendar)
        -[:CALENDAR_INCLUDES_YEAR]->(y:CalendarYear)
        -[:YEAR_INCLUDES_MONTH]->(m:CalendarMonth)
        -[:MONTH_INCLUDES_DAY]->(d:CalendarDay)
        RETURN d.unique_id as unique_id, 
               d.date as date,
               d.day_of_week as day_of_week,
               d.iso_day as iso_day,
               d.path as path
        ORDER BY d.date
        """

        result = session.run(query, user_id=user_node.unique_id)
        calendar_days = []
        for record in result:
            calendar_day = CalendarDayNode(
                unique_id=record['unique_id'],
                date=record['date'],
                day_of_week=record['day_of_week'],
                iso_day=record['iso_day'],
                path=record['path']
            )
            calendar_days.append(calendar_day)

        if not calendar_days:
            logging.error(f"No calendar days found for user {user_node.unique_id}")
        else:
            # Log the date range we have
            dates = sorted([day.date for day in calendar_days])
            logging.info(f"Found {len(calendar_days)} calendar days for user {user_node.unique_id}")
            logging.info(f"Calendar days range from {dates[0]} to {dates[-1]}")
            
        return calendar_days

def create_user_worker_timetable(
    user_node: UserNode,
    user_worker_node: TeacherNode,
    school_db_name: str
):
    """
    Create a worker timetable structure in the user's database that mirrors 
    the school timetable, with lessons linked to the user's calendar structure.
    """
    user_db_name = user_worker_node.user_db_name
    
    # Initialize filesystem and Neo4j
    fs_handler = ClassroomCopilotFilesystem(db_name=user_db_name, init_run_type="user")
    _, worker_timetable_path = fs_handler.create_teacher_timetable_directory(user_node.path)

    # Initialize neontology connection
    neon.init_neontology_connection()

    # Get user's calendar nodes
    calendar_nodes = get_user_calendar_nodes(user_db_name, user_node)
    if not calendar_nodes:
        logging.warning(f"No calendar nodes found for user {user_node.unique_id}")
        return {
            "status": "error",
            "message": "No calendar nodes found for user"
        }

    try:
        # Create UserTeacherTimetableNode
        timetable_unique_id = f"UserTeacherTimetable_{user_worker_node.teacher_code}"
        worker_timetable = UserTeacherTimetableNode(
            unique_id=timetable_unique_id,
            school_db_name=school_db_name,
            school_timetable_id=f"TeacherTimetable_{user_worker_node.teacher_code}",
            path=worker_timetable_path
        )

        # Create the timetable node
        neon.create_or_merge_neontology_node(worker_timetable, database=user_db_name, operation='merge')
        fs_handler.create_default_tldraw_file(worker_timetable.path, worker_timetable.to_dict())

        # Link timetable to teacher using the correct relationship structure
        neon.create_or_merge_neontology_relationship(
            TeacherHasTimetable(source=user_worker_node, target=worker_timetable),
            database=user_db_name,
            operation='merge'
        )
        
        # Link timetable to user using the correct relationship structure
        neon.create_or_merge_neontology_relationship(
            EntityHasTimetable(source=user_node, target=worker_timetable),
            database=user_db_name,
            operation='merge'
        )

        # Get classes from school database
        school_classes = get_school_worker_classes(school_db_name, user_node.unique_id, user_worker_node.unique_id)
        if not school_classes:
            logging.warning(f"No classes found for teacher {user_worker_node.unique_id} in school database")
            return {
                "status": "warning",
                "message": "No classes found in school database"
            }

        for class_data in school_classes:
            class_name_safe = class_data['subject_class_code'].replace(' ', '_')
            _, class_path = fs_handler.create_teacher_class_directory(worker_timetable_path, class_name_safe)

            # Create SubjectClassNode
            subject_class_node = SubjectClassNode(
                unique_id=class_data['unique_id'],
                subject_class_code=class_data['subject_class_code'],
                year_group=class_data['year_group'],
                subject=class_data['subject'],
                subject_code=class_data['subject_code'],
                path=class_path
            )
            neon.create_or_merge_neontology_node(subject_class_node, database=user_db_name, operation='merge')
            fs_handler.create_default_tldraw_file(subject_class_node.path, subject_class_node.to_dict())

            # Link class to timetable
            neon.create_or_merge_neontology_relationship(
                TimetableHasClass(source=worker_timetable, target=subject_class_node),
                database=user_db_name,
                operation='merge'
            )

            # Get periods from school database
            periods = get_school_class_periods(school_db_name, class_data['unique_id'])
            if not periods:
                logging.warning(f"No periods found for class {class_data['unique_id']} in school database")
                continue

            for period_data in periods:
                # Create UserTimetableLessonNode
                lesson_unique_id = f"UserTimetableLesson_{timetable_unique_id}_{class_name_safe}_{period_data['date']}_{period_data['period_code']}"
                timetable_lesson_node = UserTimetableLessonNode(
                    unique_id=lesson_unique_id,
                    subject_class=class_data['subject_class_code'],
                    date=period_data['date'],
                    start_time=period_data['start_time'],
                    end_time=period_data['end_time'],
                    period_code=period_data['period_code'],
                    school_db_name=school_db_name,
                    school_period_id=period_data['unique_id'],
                    path="Not set"  # Will be set after creating directories
                )

                if calendar_day := next(
                    (
                        day
                        for day in calendar_nodes
                        if day.date == period_data['date']
                    ),
                    None,
                ):
                    # Create lesson directory using calendar info
                    _, lesson_path = fs_handler.create_teacher_timetable_lesson_directory(
                        class_path,
                        f"{calendar_day.date}_{period_data['period_code']}"
                    )
                    timetable_lesson_node.path = lesson_path

                    # Create and link nodes
                    neon.create_or_merge_neontology_node(timetable_lesson_node, database=user_db_name, operation='merge')
                    fs_handler.create_default_tldraw_file(timetable_lesson_node.path, timetable_lesson_node.to_dict())

                    # Link lesson to class
                    neon.create_or_merge_neontology_relationship(
                        ClassHasLesson(source=subject_class_node, target=timetable_lesson_node),
                        database=user_db_name,
                        operation='merge'
                    )

                    # Link lesson to calendar day
                    neon.create_or_merge_neontology_relationship(
                        CalendarDayHasTimetableLesson(
                            source=calendar_day,
                            target=timetable_lesson_node
                        ),
                        database=user_db_name,
                        operation='merge'
                    )

                    neon.create_or_merge_neontology_relationship(
                        TimetableLessonBelongsToCalendarDay(
                            source=timetable_lesson_node,
                            target=calendar_day
                        ),
                        database=user_db_name,
                        operation='merge'
                    )

                    # Create PlannedLessonNode
                    planned_lesson_unique_id = f"PlannedLesson_{lesson_unique_id}"
                    _, planned_lesson_path = fs_handler.create_teacher_planned_lesson_directory(
                        class_path,
                        f"{calendar_day.date}_{period_data['period_code']}"
                    )

                    planned_lesson_node = PlannedLessonNode(
                        unique_id=planned_lesson_unique_id,
                        date=period_data['date'],
                        start_time=period_data['start_time'],
                        end_time=period_data['end_time'],
                        period_code=period_data['period_code'],
                        subject_class=class_data['subject_class_code'],
                        year_group=class_data['year_group'],
                        subject=class_data['subject'],
                        teacher_code=user_worker_node.teacher_code,
                        planning_status="Unplanned",
                        path=planned_lesson_path
                    )

                    neon.create_or_merge_neontology_node(planned_lesson_node, database=user_db_name, operation='merge')
                    fs_handler.create_default_tldraw_file(planned_lesson_node.path, planned_lesson_node.to_dict())

                    # Link planned lesson to timetable lesson
                    neon.create_or_merge_neontology_relationship(
                        TimetableLessonHasPlannedLesson(source=timetable_lesson_node, target=planned_lesson_node),
                        database=user_db_name,
                        operation='merge'
                    )

                    # Link planned lesson to calendar day
                    neon.create_or_merge_neontology_relationship(
                        CalendarDayHasPlannedLesson(
                            source=calendar_day,
                            target=planned_lesson_node
                        ),
                        database=user_db_name,
                        operation='merge'
                    )

                    neon.create_or_merge_neontology_relationship(
                        PlannedLessonBelongsToCalendarDay(
                            source=planned_lesson_node,
                            target=calendar_day
                        ),
                        database=user_db_name,
                        operation='merge'
                    )
                else:
                    logging.warning(f"No calendar day found for date {period_data['date']} - this is expected if the date is not in the current calendar year")

        logging.info(f"Successfully created user timetable structure for {user_worker_node.teacher_code}")
        return {
            "status": "success",
            "message": "User timetable structure created successfully",
            "timetable_node": worker_timetable.to_dict()
        }

    except Exception as e:
        logging.error(f"Error creating user timetable structure: {str(e)}")
        return {
            "status": "error",
            "message": f"Error creating user timetable structure: {str(e)}"
        } 