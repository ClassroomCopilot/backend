from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_database_tools_get_nodes'
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

@router.get("/get-all-nodes-and-edges")
async def get_all_nodes_and_edges():
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting all nodes and edges from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            """
            result = neo_session.run(query)
            nodes = {}
            relationships = []
            
            for record in result:
                source = record['n']
                target = record['m']
                relationship = record['r']
                
                for node in [source, target]:
                    if node.id not in nodes:
                        node_labels = list(node.labels)
                        node_type = node_labels[0] if node_labels else "Unknown"
                        node_data = dict(node)
                        try:
                            node_class = globals()[f"{node_type}Node"]
                            node_object = node_class(**node_data)
                            node_dict = node_object.to_dict()
                        except Exception as e:
                            logging.error(f"Error converting node to dict: {str(e)}")
                            node_dict = node_data
                        
                        nodes[node.id] = {
                            "node_type": node_type,
                            "node_data": node_dict
                        }
                
                relationship_info = {
                    "start_node": source.id,
                    "end_node": target.id,
                    "relationship_type": relationship.type,
                    "relationship_properties": dict(relationship)
                }
                relationships.append(relationship_info)
            
            return {
                "status": "success",
                "nodes": list(nodes.values()),
                "relationships": relationships
            }
    except Exception as e:
        logging.error(f"Error retrieving all nodes and edges: {str(e)}")
        return {"status": "error", "message": "Internal server error"}
    finally:
        driver.close_driver(neo_driver)


@router.get("/get-connected-nodes-and-edges")
async def get_connected_nodes_and_edges(unique_id: str = Query(...), db_name: str = Query(...)):
    logging.info(f"Getting connected nodes and edges for {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n {unique_id: $unique_id})
            OPTIONAL MATCH (n)-[r]-(connected)
            RETURN n, collect(connected) as connected_nodes, collect(r) as relationships
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                main_node = record['n']
                connected_nodes = record['connected_nodes']
                relationships = record['relationships']
                
                main_node_labels = list(main_node.labels)
                main_node_type = main_node_labels[0] if main_node_labels else "Unknown"
                main_node_data = dict(main_node)
                
                try:
                    main_node_class = globals()[f"{main_node_type}Node"]
                    main_node_object = main_node_class(**main_node_data)
                    main_node_dict = main_node_object.to_dict()
                except Exception as e:
                    logging.error(f"Error converting main node to dict: {str(e)}")
                    main_node_dict = main_node_data
                
                connected_nodes_list = []
                relationship_list = []
                
                for node, relationship in zip(connected_nodes, relationships):
                    node_labels = list(node.labels)
                    node_type = node_labels[0] if node_labels else "Unknown"
                    node_data = dict(node)
                    try:
                        node_class = globals()[f"{node_type}Node"]
                        node_object = node_class(**node_data)
                        connected_node_dict = node_object.to_dict()
                    except Exception as e:
                        logging.error(f"Error converting connected node to dict: {str(e)}")
                        connected_node_dict = node_data
                    
                    connected_node_info = {
                        "node_type": node_type,
                        "node_data": connected_node_dict,
                        "relationship_type": relationship.type,  # Get relationship type
                        "relationship_properties": dict(relationship)  # Relationship properties, if any
                    }
                    connected_nodes_list.append(connected_node_info)

                    relationship_info = {
                        "start_node": dict(relationship.start_node),
                        "end_node": dict(relationship.end_node),
                        "relationship_type": relationship.type,
                        "relationship_properties": dict(relationship)
                    }
                    relationship_list.append(relationship_info)
                
                logging.info(f"Main node: {main_node_dict}")
                logging.info(f"Connected nodes: {connected_nodes_list}")
                logging.info(f"Relationships: {relationship_list}")
                
                return {
                    "status": "success",
                    "main_node": {
                        "node_type": main_node_type,
                        "node_data": main_node_dict
                    },
                    "connected_nodes": connected_nodes_list,
                    "relationships": relationship_list
                }
            else:
                return {"status": "not_found", "message": "Node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)