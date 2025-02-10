import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

def get_static_nodes(context: str, db_name: str) -> List[Dict[str, Any]]:
    """Get static nodes for a specific context."""
    if context == 'workers':
        # For workers context, show teacher node first, then timetables and classes
        query = """
        MATCH (t:Teacher)
        RETURN DISTINCT {
            id: t.unique_id,
            path: t.path,
            label: t.teacher_name_formal,
            type: 'Teacher',
            isStatic: true,
            order: 0,
            section: 'Root'
        } as node
        UNION ALL
        MATCH (t:UserTeacherTimetable)
        RETURN DISTINCT {
            id: t.unique_id,
            path: t.path,
            label: t.name,
            type: 'UserTeacherTimetable',
            isStatic: true,
            order: 1,
            section: 'Timetables'
        } as node
        UNION ALL
        MATCH (t:UserTeacherTimetable)-[:HAS_CLASS]->(c:Class)
        RETURN DISTINCT {
            id: c.unique_id,
            path: c.path,
            label: c.name,
            type: 'Class',
            isStatic: true,
            order: 2,
            section: 'Classes'
        } as node
        """
    elif context == 'user':
        # For user context, show the user node
        query = """
        MATCH (u:User)
        RETURN DISTINCT {
            id: u.unique_id,
            path: u.path,
            label: u.user_name,
            type: 'User',
            isStatic: true,
            order: 0,
            section: 'Root'
        } as node
        """
    else:
        # For calendar context, show today's calendar node first, then other calendar nodes
        today = datetime.now().strftime("%Y-%m-%d")
        query = """
        MATCH (n:Calendar)
        WITH n, 
        CASE 
            WHEN date($today) >= date(n.start_date) AND date($today) <= date(n.end_date) 
            THEN 0 
            ELSE 1 
        END as nodeOrder
        RETURN DISTINCT {
            id: n.unique_id,
            path: n.path,
            label: n.name,
            type: 'Calendar',
            isStatic: true,
            order: nodeOrder,
            section: CASE nodeOrder 
                WHEN 0 THEN 'Today'
                ELSE 'Calendar'
            END
        } as node
        ORDER BY node.order, node.label
        """ 

    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, today=datetime.now().strftime("%Y-%m-%d"))
            return [record["node"] for record in result]
    except Exception as e:
        logger.error(f"Error getting static nodes: {str(e)}")
        return []

def get_today_calendar_node(db_name: str) -> Optional[Dict[str, Any]]:
    """Get today's calendar node."""
    today = datetime.now().strftime("%Y-%m-%d")
    query = """
    MATCH (n:Calendar)
    WHERE date($today) >= date(n.start_date) AND date($today) <= date(n.end_date)
    RETURN n.unique_id as id, n.path as path, n.name as label, 
           'Calendar' as type
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, today=today)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting today's calendar node: {str(e)}")
        return None

def get_relative_calendar_node(day_offset: int, db_name: str) -> Optional[Dict[str, Any]]:
    """Get calendar node relative to today."""
    target_date = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
    query = """
    MATCH (n:Calendar)
    WHERE date($target_date) >= date(n.start_date) AND date($target_date) <= date(n.end_date)
    RETURN n.unique_id as id, n.path as path, n.name as label, 
           'Calendar' as type
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, target_date=target_date)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting relative calendar node: {str(e)}")
        return None

def get_next_month_node(db_name: str) -> Optional[Dict[str, Any]]:
    """Get next month's calendar node."""
    next_month_start = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")
    query = """
    MATCH (n:Calendar)
    WHERE date($next_month_start) >= date(n.start_date) AND date($next_month_start) <= date(n.end_date)
    RETURN n.unique_id as id, n.path as path, n.name as label, 
           'Calendar' as type
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, next_month_start=next_month_start)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting next month node: {str(e)}")
        return None

def get_previous_month_node(db_name: str) -> Optional[Dict[str, Any]]:
    """Get previous month's calendar node."""
    prev_month_start = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
    query = """
    MATCH (n:Calendar)
    WHERE date($prev_month_start) >= date(n.start_date) AND date($prev_month_start) <= date(n.end_date)
    RETURN n.unique_id as id, n.path as path, n.name as label, 
           'Calendar' as type
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, prev_month_start=prev_month_start)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting previous month node: {str(e)}")
        return None

def get_user_timetables(db_name: str) -> List[Dict[str, Any]]:
    """Get user's timetables."""
    query = """
    MATCH (t:UserTeacherTimetable)
    RETURN t.unique_id as id, t.path as path, t.name as label, 
           'UserTeacherTimetable' as type
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            return [dict(record) for record in result]
    except Exception as e:
        logger.error(f"Error getting user timetables: {str(e)}")
        return []

def get_timetable_classes(timetable_id: str, db_name: str) -> List[Dict[str, Any]]:
    """Get classes for a timetable."""
    query = """
    MATCH (t:UserTeacherTimetable {unique_id: $timetable_id})-[:HAS_CLASS]->(c:Class)
    RETURN c.unique_id as id, c.path as path, c.name as label, 
           'Class' as type
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, timetable_id=timetable_id)
            return [dict(record) for record in result]
    except Exception as e:
        logger.error(f"Error getting timetable classes: {str(e)}")
        return []

def get_next_lesson(class_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get next lesson for a class."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    query = """
    MATCH (c:Class {unique_id: $class_id})-[:HAS_LESSON]->(l:Lesson)
    WHERE l.start_time > $now
    RETURN l.unique_id as id, l.path as path, l.name as label, 
           'Lesson' as type
    ORDER BY l.start_time ASC
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, class_id=class_id, now=now)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting next lesson: {str(e)}")
        return None

def get_previous_lesson(class_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get previous lesson for a class."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    query = """
    MATCH (c:Class {unique_id: $class_id})-[:HAS_LESSON]->(l:Lesson)
    WHERE l.start_time < $now
    RETURN l.unique_id as id, l.path as path, l.name as label, 
           'Lesson' as type
    ORDER BY l.start_time DESC
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, class_id=class_id, now=now)
            record = result.single()
            return dict(record) if record else None
    except Exception as e:
        logger.error(f"Error getting previous lesson: {str(e)}")
        return None

def save_shared_snapshot(path: str, room_id: str, snapshot: Dict[str, Any]) -> bool:
    """Save snapshot to a shared room."""
    try:
        # Save the snapshot to the shared room's storage
        session_tools.save_tldraw_node_file(path, room_id, snapshot)
        return True
    except Exception as e:
        logger.error(f"Error saving shared snapshot: {str(e)}")
        return False

def get_connected_nodes_for_workers(node_id: str, db_name: str) -> List[Dict[str, Any]]:
    """Get connected nodes specific to the workers context."""
    query = """
    MATCH (n {unique_id: $node_id})
    WITH n
    CALL {
        WITH n
        MATCH (n:UserTeacherTimetable)-[:HAS_CLASS]->(c:Class)
        RETURN c.unique_id as id, c.path as path, c.name as label, 
               'Class' as type
        UNION
        MATCH (n:Class)<-[:HAS_CLASS]-(t:UserTeacherTimetable)
        RETURN t.unique_id as id, t.path as path, t.name as label, 
               'UserTeacherTimetable' as type
        UNION
        MATCH (n:Class)-[:HAS_LESSON]->(l:Lesson)
        RETURN l.unique_id as id, l.path as path, l.name as label, 
               'Lesson' as type
    }
    RETURN DISTINCT id, path, label, type
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, node_id=node_id)
            return [dict(record) for record in result]
    except Exception as e:
        logger.error(f"Error getting connected nodes for workers: {str(e)}")
        return []

def get_connected_nodes(node_id: str, db_name: str, context: str = None) -> List[Dict[str, Any]]:
    """Get connected nodes based on context."""
    if context == 'workers':
        return get_connected_nodes_for_workers(node_id, db_name)
    
    # Default query for other contexts
    query = """
    MATCH (n {unique_id: $node_id})-[r]-(connected)
    RETURN DISTINCT connected.unique_id as id, connected.path as path, 
           connected.name as label, labels(connected)[0] as type
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, node_id=node_id)
            return [dict(record) for record in result]
    except Exception as e:
        logger.error(f"Error getting connected nodes: {str(e)}")
        return []

## Worker Navigation

def get_worker_structure(db_name: str) -> Dict[str, Any]:
    """Get the complete worker structure including schools, departments, timetables, classes, and lessons."""
    try:
        query = """
        // Match all worker-related nodes
        MATCH (s:School)
        OPTIONAL MATCH (s)-[:HAS_DEPARTMENT]->(d:Department)
        OPTIONAL MATCH (d)-[:HAS_TIMETABLE]->(t:UserTeacherTimetable)
        OPTIONAL MATCH (t)-[:HAS_CLASS]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_LESSON]->(l:TimetableLesson)
        WITH s, d, t, c, l
        ORDER BY s.school_name, d.department_code, t.name, c.class_code, l.start_time

        // Collect all nodes
        RETURN {
            schools: collect(DISTINCT {
                id: s.unique_id,
                path: s.path,
                name: s.school_name,
                __primarylabel__: 'School'
            }),
            departments: collect(DISTINCT {
                id: d.unique_id,
                path: d.path,
                code: d.department_code,
                school_id: s.unique_id,
                __primarylabel__: 'Department'
            }),
            timetables: collect(DISTINCT {
                id: t.unique_id,
                path: t.path,
                name: t.name,
                department_id: d.unique_id,
                __primarylabel__: 'UserTeacherTimetable'
            }),
            classes: collect(DISTINCT {
                id: c.unique_id,
                path: c.path,
                code: c.class_code,
                timetable_id: t.unique_id,
                __primarylabel__: 'Class'
            }),
            lessons: collect(DISTINCT {
                id: l.unique_id,
                path: l.path,
                start_time: l.start_time,
                class_id: c.unique_id,
                __primarylabel__: 'TimetableLesson'
            })
        } as structure
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            record = result.single()
            if not record:
                logger.error('No worker structure found')
                return None
            
            return {
                "status": "success",
                "structure": record["structure"]
            }

    except Exception as e:
        logger.error(f"Error getting worker structure: {str(e)}")
        return None

def get_school_node(school_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific school node."""
    query = """
    MATCH (s:School {unique_id: $school_id})
    RETURN {
        id: s.unique_id,
        path: s.path,
        name: s.school_name,
        __primarylabel__: 'School'
    } as node
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, school_id=school_id)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting school node: {str(e)}")
        return None

def get_department_node(dept_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific department node."""
    query = """
    MATCH (d:Department {unique_id: $dept_id})
    RETURN {
        id: d.unique_id,
        path: d.path,
        code: d.department_code,
        __primarylabel__: 'Department'
    } as node
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, dept_id=dept_id)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting department node: {str(e)}")
        return None

def get_timetable_node(timetable_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific timetable node."""
    query = """
    MATCH (t:UserTeacherTimetable {unique_id: $timetable_id})
    RETURN {
        id: t.unique_id,
        path: t.path,
        name: t.name,
        __primarylabel__: 'UserTeacherTimetable'
    } as node
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, timetable_id=timetable_id)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting timetable node: {str(e)}")
        return None

def get_class_node(class_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific class node."""
    query = """
    MATCH (c:Class {unique_id: $class_id})
    RETURN {
        id: c.unique_id,
        path: c.path,
        code: c.class_code,
        __primarylabel__: 'Class'
    } as node
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, class_id=class_id)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting class node: {str(e)}")
        return None

def get_lesson_node(lesson_id: str, db_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific lesson node."""
    query = """
    MATCH (l:TimetableLesson {unique_id: $lesson_id})
    RETURN {
        id: l.unique_id,
        path: l.path,
        start_time: l.start_time,
        __primarylabel__: 'TimetableLesson'
    } as node
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, lesson_id=lesson_id)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting lesson node: {str(e)}")
        return None

def get_current_lesson(db_name: str) -> Optional[Dict[str, Any]]:
    """Get the current or next upcoming lesson."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    query = """
    MATCH (l:TimetableLesson)
    WHERE l.start_time >= $now
    RETURN {
        id: l.unique_id,
        path: l.path,
        start_time: l.start_time,
        __primarylabel__: 'TimetableLesson'
    } as node
    ORDER BY l.start_time ASC
    LIMIT 1
    """
    try:
        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, now=now)
            record = result.single()
            return record["node"] if record else None
    except Exception as e:
        logger.error(f"Error getting current lesson: {str(e)}")
        return None