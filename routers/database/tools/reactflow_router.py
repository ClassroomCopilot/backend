from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_tools_reactflow_router'
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
import modules.database.tools.neo4j_session_tools as session
from modules.database.schemas.calendar_neo import CalendarNode, CalendarYearNode, CalendarMonthNode, CalendarWeekNode, CalendarDayNode, CalendarTimeChunkNode
from modules.database.schemas.curriculum_neo import PastoralStructureNode, YearGroupNode, CurriculumStructureNode, KeyStageNode, KeyStageSyllabusNode, YearGroupSyllabusNode, SubjectNode, TopicNode, TopicLessonNode, LearningStatementNode, ScienceLabNode
from modules.database.schemas.timetable_neo import SchoolTimetableNode, AcademicYearNode, AcademicTermNode, AcademicWeekNode, AcademicDayNode, OffTimetableDayNode, StaffDayNode, AcademicPeriodNode, RegistrationPeriodNode, OffTimetablePeriodNode, AcademicTermBreakNode, BreakPeriodNode, HolidayDayNode, HolidayWeekNode
from modules.database.schemas.entity_neo import UserNode, StandardUserNode, DeveloperNode, SchoolAdminNode, SchoolNode, DepartmentNode, TeacherNode, StudentNode, SubjectClassNode, RoomNode
from modules.database.schemas.teacher_timetable_neo import TeacherTimetableNode, TimetableLessonNode, PlannedLessonNode
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

@router.get("/get-teacher-timetable-classes")
async def get_teacher_timetable_classes(unique_id: str = Query(...)):
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting teacher timetable classes for {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (t:User {unique_id: $unique_id})-[:IS]->(teacher:Teacher)
            MATCH (teacher)-[:TEACHER_HAS_TIMETABLE]->(tt:TeacherTimetable)
            MATCH (tt)-[r:TIMETABLE_HAS_CLASS]->(sc:SubjectClass)
            RETURN t, teacher, tt, collect({relationship: r, subject_class: sc}) as classes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            
            if record:
                user = record['t']
                teacher = record['teacher']
                timetable = record['tt']
                classes = record['classes']
                
                nodes = []
                relationships = []
                
                # Process User node
                user_dict = UserNode(**dict(user)).to_dict()
                nodes.append({"node_type": "User", "node_data": user_dict})
                
                # Process Teacher node
                teacher_dict = TeacherNode(**dict(teacher)).to_dict()
                nodes.append({"node_type": "Teacher", "node_data": teacher_dict})
                
                # Process TeacherTimetable node
                timetable_dict = TeacherTimetableNode(**dict(timetable)).to_dict()
                nodes.append({"node_type": "TeacherTimetable", "node_data": timetable_dict})
                
                # Process User-Teacher relationship
                relationships.append({
                    "start_node": user_dict,
                    "end_node": teacher_dict,
                    "relationship_type": "IS",
                    "relationship_properties": {}
                })
                
                # Process Teacher-Timetable relationship
                relationships.append({
                    "start_node": teacher_dict,
                    "end_node": timetable_dict,
                    "relationship_type": "TEACHER_HAS_TIMETABLE",
                    "relationship_properties": {}
                })
                
                # Process SubjectClass nodes and relationships
                for class_info in classes:
                    subject_class = class_info['subject_class']
                    relationship = class_info['relationship']
                    
                    subject_class_dict = SubjectClassNode(**dict(subject_class)).to_dict()
                    nodes.append({"node_type": "SubjectClass", "node_data": subject_class_dict})
                    
                    relationships.append({
                        "start_node": timetable_dict,
                        "end_node": subject_class_dict,
                        "relationship_type": "TIMETABLE_HAS_CLASS",
                        "relationship_properties": dict(relationship)
                    })
                
                return {
                    "status": "success",
                    "message": "Teacher timetable classes retrieved successfully",
                    "nodes": nodes,
                    "relationships": relationships
                }
            else:
                return {"status": "not_found", "message": "Teacher or timetable not found"}
    except Exception as e:
        logging.error(f"Error getting teacher timetable classes: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        driver.close_driver(neo_driver)