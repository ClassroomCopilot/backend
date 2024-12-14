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
from modules.database.schemas.calendar_neo import CalendarNode
from modules.database.schemas.timetable_neo import SchoolTimetableNode, AcademicYearNode, AcademicTermNode, AcademicWeekNode, AcademicDayNode, AcademicPeriodNode, RegistrationPeriodNode
from modules.database.schemas.entity_neo import UserNode, StandardUserNode, DeveloperNode, SchoolAdminNode, SchoolNode, DepartmentNode, TeacherNode, StudentNode, SubjectClassNode, RoomNode
from modules.database.schemas.teacher_timetable_neo import TeacherTimetableNode, TimetableLessonNode, PlannedLessonNode
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

@router.get("/get-user-node")
async def get_user_node(user_id: str = Query(...)):
    db_name = f"cc.ccusers.{user_id}"
    logging.info(f"Getting user node for user {user_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            nodes = session.find_nodes_by_label_and_properties(neo_session, "User", {"user_id": user_id})
            if nodes:
                user_node = nodes[0]
                data = UserNode(**user_node)
                user_node_data = data.to_dict()
                return {"status": "success", "user_node": user_node_data, "user_node_raw": nodes}
            else:
                return {"status": "not_found", "message": "User node not found"}
    except Exception as e:
        logging.error(f"Error retrieving user node: {str(e)}")
        return {"status": "error", "message": "Internal server error"}
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-connected-nodes")
async def get_connected_nodes(unique_id: str = Query(...), db_name: str = Query(...)):
    logging.info(f"Getting connected nodes for {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n {unique_id: $unique_id})
            OPTIONAL MATCH (n)-[]-(connected)
            RETURN n, collect(connected) as connected_nodes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                main_node = record['n']
                connected_nodes = record['connected_nodes']
                
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
                
                for node in connected_nodes:
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
                        "node_data": connected_node_dict
                    }
                    connected_nodes_list.append(connected_node_info)
                
                logging.debug(f"connected_nodes_list: {connected_nodes_list}")
                
                return {
                    "status": "success",
                    "main_node": {
                        "node_type": main_node_type,
                        "node_data": main_node_dict
                    },
                    "connected_nodes": connected_nodes_list
                }
            else:
                return {"status": "not_found", "message": "Node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-user-connected-nodes")
async def get_user_connected_nodes(unique_id: str = Query(...)):
    logging.info(f"Getting user adjacent nodes for node {unique_id}")
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai") # TODO: This function needs to be able to take a db_name as a parameter
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")
    try:
        with neo_driver.session(database=db_name) as neo_session:
            user_node_and_connected_nodes = session.get_node_by_unique_id_and_adjacent_nodes(neo_session, unique_id)
            user_node = user_node_and_connected_nodes['node']
            connected_nodes = user_node_and_connected_nodes['connected_nodes']
            try:
                data = UserNode(**user_node)
                user_node_dict = data.to_dict()
            except Exception as e:
                logging.error(f"Error converting user node to dict: {str(e)}")
            connected_nodes_list = []
            for connected_node in connected_nodes:
                node_data = connected_node['node']
                node_labels = list(node_data.labels)
                logging.debug(f"node_labels: {node_labels}")
                for label in node_labels:
                    logging.debug(f"label: {label}")
                    try:
                        if 'Developer' == label:
                            logging.debug(f"Developer node found")
                            node_object = DeveloperNode(**node_data)
                        elif 'StandardUser' == label:
                            logging.debug(f"StandardUser node found")
                            node_object = StandardUserNode(**node_data)
                        elif 'SchoolAdmin' == label:
                            logging.debug(f"SchoolAdmin node found")
                            node_object = SchoolAdminNode(**node_data)
                        elif 'Teacher' == label:
                            logging.debug(f"Teacher node found")
                            node_object = TeacherNode(**node_data)
                        elif 'Student' == label:
                            logging.debug(f"Student node found")
                            node_object = StudentNode(**node_data)
                        elif 'Calendar' == label:
                            logging.debug(f"Calendar node found")
                            node_object = CalendarNode(**node_data)
                        elif 'TeacherTimetable' == label:
                            logging.debug(f"TeacherTimetable node found")
                            node_object = TeacherTimetableNode(**node_data)
                        elif 'School' == label:
                            logging.debug(f"School node found")
                            node_object = SchoolNode(**node_data)
                        elif 'Department' == label:
                            logging.debug(f"Department node found")
                            node_object = DepartmentNode(**node_data)
                        elif 'Student' == label:
                            logging.debug(f"Student node found")
                            node_object = StudentNode(**node_data)
                        elif 'Class' == label:
                            logging.debug(f"Class node found")
                            node_object = SubjectClassNode(**node_data)
                        elif 'Room' == label:
                            logging.debug(f"Room node found")
                            node_object = RoomNode(**node_data)
                        else:
                            logging.error(f"Unknown node label: {node_labels}")
                            continue
                        connected_node_dict = node_object.to_dict()
                        logging.debug(f"connected_node_dict: {connected_node_dict}")
                        connected_node_info = {
                            "node_type": label,
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
            return {"status": "success", "user_node": user_node_dict, "user_connected_nodes": connected_nodes_list}
    except Exception as e:
        logging.error(f"Error retrieving adjacent nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-worker-connected-nodes")
async def get_worker_connected_nodes(unique_id: str = Query(...)):
    logging.info(f"Getting worker adjacent nodes for node {unique_id}")
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai") # TODO: This function needs to be able to take a db_name as a parameter
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        raise HTTPException(status_code=500, detail="Failed to connect to the database")
    try:
        with neo_driver.session(database=db_name) as neo_session:
            node_and_connected_nodes = session.get_node_by_unique_id_and_adjacent_nodes(neo_session, unique_id)
            worker_node = node_and_connected_nodes['node']
            connected_nodes = node_and_connected_nodes['connected_nodes']
            try:
                data = TeacherNode(**worker_node)
                worker_node_dict = data.to_dict()
            except Exception as e:
                logging.error(f"Error converting user node to dict: {str(e)}")
            connected_nodes_list = []
            for connected_node in connected_nodes:
                node_data = connected_node['node']
                node_labels = list(node_data.labels)
                logging.debug(f"node_labels: {node_labels}")
                for label in node_labels:
                    logging.debug(f"label: {label}")
                    try:
                        if 'Calendar' == label:
                            logging.debug(f"Calendar node found")
                            node_object = CalendarNode(**node_data)
                        elif 'TeacherTimetable' == label:
                            logging.debug(f"TeacherTimetable node found")
                            node_object = TeacherTimetableNode(**node_data)
                        elif 'School' == label:
                            logging.debug(f"School node found")
                            node_object = SchoolNode(**node_data)
                        elif 'Department' == label:
                            logging.debug(f"Department node found")
                            node_object = DepartmentNode(**node_data)
                        elif 'Student' == label:
                            logging.debug(f"Student node found")
                            node_object = StudentNode(**node_data)
                        elif 'Class' == label:
                            logging.debug(f"Class node found")
                            node_object = SubjectClassNode(**node_data)
                        elif 'Room' == label:
                            logging.debug(f"Room node found")
                            node_object = RoomNode(**node_data)
                        else:
                            logging.error(f"Unknown node label: {node_labels}")
                            continue
                        connected_node_dict = node_object.to_dict()
                        logging.debug(f"connected_node_dict: {connected_node_dict}")
                        connected_node_info = {
                            "node_type": label,
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
            return {"status": "success", "user_node": worker_node_dict, "worker_connected_nodes": connected_nodes_list}
    except Exception as e:
        logging.error(f"Error retrieving worker adjacent nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-calendar-connected-nodes")
async def get_calendar_connected_nodes(unique_id: str = Query(...)):
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting connected nodes for calendar {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n)
            WHERE n.unique_id = $unique_id AND (n:Calendar OR n:CalendarYear OR n:CalendarMonth OR n:CalendarWeek OR n:CalendarDay OR n:CalendarTimeChunk)
            OPTIONAL MATCH (n)-[]-(connected)
            RETURN n, collect(connected) as connected_nodes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                calendar_node = record['n']
                connected_nodes = record['connected_nodes']
                
                node_type = list(calendar_node.labels)[0]
                calendar_dict = globals()[f"{node_type}Node"](**calendar_node).to_dict()
                connected_nodes_list = []
                
                for node in connected_nodes:
                    node_labels = list(node.labels)
                    node_data = dict(node)
                    try:
                        node_class = globals()[f"{node_labels[0]}Node"]
                        node_object = node_class(**node_data)
                        connected_node_dict = node_object.to_dict()
                        connected_node_info = {
                            "node_type": node_labels[0],
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
                
                return {"status": "success", "calendar_node": calendar_dict, "connected_nodes": connected_nodes_list}
            else:
                return {"status": "not_found", "message": "Calendar node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)
    
@router.get("/get-teacher-timetable-connected-nodes")
async def get_teacher_timetable_connected_nodes(unique_id: str = Query(...)):
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting connected nodes for teacher timetable {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n:TeacherTimetable {unique_id: $unique_id})
            OPTIONAL MATCH (n)-[]-(connected)
            RETURN n, collect(connected) as connected_nodes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                teacher_timetable_node = record['n']
                connected_nodes = record['connected_nodes']
                
                teacher_timetable_dict = TeacherTimetableNode(**teacher_timetable_node).to_dict()
                connected_nodes_list = []
                
                for node in connected_nodes:
                    node_labels = list(node.labels)
                    node_data = dict(node)
                    try:
                        if 'TimetableLesson' in node_labels:
                            node_object = TimetableLessonNode(**node_data)
                        elif 'PlannedLesson' in node_labels:
                            node_object = PlannedLessonNode(**node_data)
                        else:
                            logging.error(f"Unknown node label: {node_labels}")
                            continue
                        connected_node_dict = node_object.to_dict()
                        connected_node_info = {
                            "node_type": node_labels[0],
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
                
                return {"status": "success", "teacher_timetable_node": teacher_timetable_dict, "connected_nodes": connected_nodes_list}
            else:
                return {"status": "not_found", "message": "Teacher timetable node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-school-timetable-connected-nodes")
async def get_school_timetable_connected_nodes(unique_id: str = Query(...)):
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting connected nodes for school timetable {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n:SchoolTimetable {unique_id: $unique_id})
            OPTIONAL MATCH (n)-[]-(connected)
            RETURN n, collect(connected) as connected_nodes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                school_timetable_node = record['n']
                connected_nodes = record['connected_nodes']
                
                school_timetable_dict = SchoolTimetableNode(**school_timetable_node).to_dict()
                connected_nodes_list = []
                
                for node in connected_nodes:
                    node_labels = list(node.labels)
                    node_data = dict(node)
                    try:
                        if 'AcademicYear' in node_labels:
                            node_object = AcademicYearNode(**node_data)
                        elif 'AcademicTerm' in node_labels:
                            node_object = AcademicTermNode(**node_data)
                        elif 'AcademicWeek' in node_labels:
                            node_object = AcademicWeekNode(**node_data)
                        elif 'AcademicDay' in node_labels:
                            node_object = AcademicDayNode(**node_data)
                        elif 'AcademicPeriod' in node_labels:
                            node_object = AcademicPeriodNode(**node_data)
                        elif 'RegistrationPeriod' in node_labels:
                            node_object = RegistrationPeriodNode(**node_data)
                        else:
                            logging.error(f"Unknown node label: {node_labels}")
                            continue
                        connected_node_dict = node_object.to_dict()
                        connected_node_info = {
                            "node_type": node_labels[0],
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
                
                return {"status": "success", "school_timetable_node": school_timetable_dict, "connected_nodes": connected_nodes_list}
            else:
                return {"status": "not_found", "message": "School timetable node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-curriculum-connected-nodes")
async def get_curriculum_connected_nodes(unique_id: str = Query(...)):
    db_name = os.getenv("NEO4J_DB_NAME", "cc.ccschools.kevlarai")
    logging.info(f"Getting connected nodes for curriculum {unique_id} from database {db_name}")
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            query = """
            MATCH (n)
            WHERE n.unique_id = $unique_id AND (n:PastoralStructure OR n:YearGroup OR n:CurriculumStructure OR n:KeyStage OR n:KeyStageSyllabus OR n:YearGroupSyllabus OR n:Subject OR n:Topic OR n:TopicLesson OR n:LearningStatement OR n:ScienceLab)
            OPTIONAL MATCH (n)-[]-(connected)
            RETURN n, collect(connected) as connected_nodes
            """
            result = neo_session.run(query, unique_id=unique_id)
            record = result.single()
            if record:
                curriculum_node = record['n']
                connected_nodes = record['connected_nodes']
                
                node_type = list(curriculum_node.labels)[0]
                curriculum_dict = globals()[f"{node_type}Node"](**curriculum_node).to_dict()
                connected_nodes_list = []
                
                for node in connected_nodes:
                    node_labels = list(node.labels)
                    node_data = dict(node)
                    try:
                        node_class = globals()[f"{node_labels[0]}Node"]
                        node_object = node_class(**node_data)
                        connected_node_dict = node_object.to_dict()
                        connected_node_info = {
                            "node_type": node_labels[0],
                            "node_data": connected_node_dict
                        }
                        connected_nodes_list.append(connected_node_info)
                    except Exception as e:
                        logging.error(f"Error converting node to dict: {str(e)}")
                
                return {"status": "success", "curriculum_node": curriculum_dict, "connected_nodes": connected_nodes_list}
            else:
                return {"status": "not_found", "message": "Curriculum node not found"}
    except Exception as e:
        logging.error(f"Error retrieving connected nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        driver.close_driver(neo_driver)

@router.get("/get-school-node")
async def get_school_node(school_uuid: str = Query(...)):
    logging.info(f"Getting school node for school {school_uuid}...")
    db_name = f"cc.ccschools.{school_uuid}"
    neo_driver = driver.get_driver(db_name=db_name)
    if neo_driver is None:
        return {"status": "error", "message": "Failed to connect to the database"}
    
    try:
        with neo_driver.session(database=db_name) as neo_session:
            nodes = session.find_nodes_by_label_and_properties(neo_session, "School", {"school_uuid": school_uuid})
            if nodes:
                school_node = nodes[0]
                data = SchoolNode(
                    unique_id=school_node["unique_id"],
                    school_uuid=school_node["school_uuid"],
                    school_name=school_node["school_name"],
                    school_website=school_node["school_website"],
                    path=school_node["path"]
                )
                school_node_data = data.to_dict()
                return {"status": "success", "school_node": school_node_data, "school_node_raw": nodes}
            else:
                return {"status": "not_found", "message": "School node not found"}
    except Exception as e:
        logging.error(f"Error retrieving school node: {str(e)}")
        return {"status": "error", "message": "Internal server error"}
    finally:
        driver.close_driver(neo_driver)