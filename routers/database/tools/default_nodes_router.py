from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from modules.database.tools import neo4j_driver_tools as driver_tools
from modules.logger_tool import initialise_logger
from neo4j.time import DateTime, Date
import os
from datetime import datetime

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
router = APIRouter()

def convert_neo4j_values(value: Any) -> Any:
    """Convert Neo4j types to JSON-serializable types."""
    if isinstance(value, DateTime):
        return value.isoformat()  # Convert to ISO format string
    elif isinstance(value, Date):
        return value.isoformat()  # Convert Date to ISO format string
    elif isinstance(value, dict):
        return {k: convert_neo4j_values(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_neo4j_values(v) for v in value]
    return value

def get_default_node_week(db_name: str) -> Dict[str, Any]:
    """Get the current week node."""
    # Get today's date
    today = datetime.now()
    
    # Find the calendar week node that contains today's date
    query = """
    MATCH (w:CalendarWeek)
    WHERE date(w.start_date) <= date($today) AND date($today) <= date(w.start_date) + duration('P7D')
    RETURN w
    """
    
    with driver_tools.get_session(database=db_name) as session:
        result = session.run(query, today=today.strftime('%Y-%m-%d'))
        week_node = result.single()
        
        if not week_node:
            raise HTTPException(status_code=404, detail="No default node found for context: week")
            
        node = week_node["w"]
        node_data = dict(node)
        converted_data = convert_neo4j_values(node_data)
        
        return {
            "status": "success",
            "node": {
                "id": node["unique_id"],
                "path": node["path"],
                "type": "CalendarWeek",
                "label": node.get("title", "Calendar Week"),
                "data": converted_data
            }
        }

def get_default_node_month(db_name: str) -> Dict[str, Any]:
    """Get the current month node."""
    # Get today's date
    today = datetime.now()
    
    # Find the calendar month node for the current month
    query = """
    MATCH (m:CalendarMonth)
    WHERE m.year = $year AND m.month = $month
    RETURN m
    """
    
    with driver_tools.get_session(database=db_name) as session:
        result = session.run(query, year=str(today.year), month=str(today.month))
        month_node = result.single()
        
        if not month_node:
            raise HTTPException(status_code=404, detail="No default node found for context: month")
            
        node = month_node["m"]
        node_data = dict(node)
        converted_data = convert_neo4j_values(node_data)
        
        return {
            "status": "success",
            "node": {
                "id": node["unique_id"],
                "path": node["path"],
                "type": "CalendarMonth",
                "label": node.get("title", "Calendar Month"),
                "data": converted_data
            }
        }

@router.get("/get-default-node/{context}")
async def get_default_node(context: str, db_name: str, base_context: str | None = None) -> Dict[str, Any]:
    """Get the default node for a given context."""
    try:
        # Handle special cases for week and month
        if context == 'week':
            return get_default_node_week(db_name)
        elif context == 'month':
            return get_default_node_month(db_name)

        # Map contexts to their default node queries
        context_queries = {
            # Base Contexts
            'profile': """
                MATCH (n:User)
                RETURN n LIMIT 1
            """,
            'calendar': """
                MATCH (n:Calendar)
                RETURN n LIMIT 1
            """,
            'teaching': """
                MATCH (n:Teacher)
                RETURN n LIMIT 1
            """,
            'school': """
                MATCH (n:School)
                RETURN n LIMIT 1
            """,
            'department': """
                MATCH (n:Department)
                RETURN n LIMIT 1
            """,
            'class': """
                MATCH (n:Class)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - Overview queries for each base context
            'overview': """
                MATCH (n)
                WHERE CASE $base_context
                    WHEN 'profile' THEN n:User
                    WHEN 'calendar' THEN n:Calendar
                    WHEN 'teaching' THEN n:Teacher
                    WHEN 'school' THEN n:School
                    WHEN 'department' THEN n:Department
                    WHEN 'class' THEN n:Class
                    ELSE false
                END
                RETURN n LIMIT 1
            """,

            # Extended Contexts - User
            'settings': """
                MATCH (n:User)
                RETURN n LIMIT 1
            """,
            'history': """
                MATCH (n:User)
                RETURN n LIMIT 1
            """,
            'journal': """
                MATCH (n:Journal)
                RETURN n LIMIT 1
            """,
            'planner': """
                MATCH (n:Planner)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - Calendar
            'day': """
                MATCH (n:CalendarDay)
                WHERE date(n.date) = date()
                RETURN n LIMIT 1
            """,
            'year': """
                MATCH (n:CalendarYear)
                WHERE n.year = toString(date().year)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - Teaching
            'timetable': """
                MATCH (n:UserTeacherTimetable)
                RETURN n LIMIT 1
            """,
            'classes': """
                MATCH (n:Class)
                RETURN n LIMIT 1
            """,
            'lessons': """
                MATCH (n:TimetableLesson)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - School
            'departments': """
                MATCH (n:Department)
                RETURN n LIMIT 1
            """,
            'staff': """
                MATCH (n:Teacher)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - Department
            'teachers': """
                MATCH (n:Teacher)
                RETURN n LIMIT 1
            """,
            'subjects': """
                MATCH (n:Subject)
                RETURN n LIMIT 1
            """,

            # Extended Contexts - Class
            'students': """
                MATCH (n:Student)
                RETURN n LIMIT 1
            """
        }

        if context not in context_queries:
            raise HTTPException(status_code=400, detail=f"Invalid context: {context}")

        query = context_queries[context]
        
        with driver_tools.get_session(database=db_name) as session:
            # For overview context, we need to pass the database name as a parameter
            params = {'db_name': db_name, 'base_context': base_context} if context == 'overview' else {}
            result = session.run(query, params)
            record = result.single()
            
            if not record:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No default node found for context: {context}"
                )
            
            node = record["n"]
            node_data = dict(node)
            
            # Convert Neo4j types to JSON-serializable types
            converted_data = convert_neo4j_values(node_data)
            
            return {
                "status": "success",
                "node": {
                    "id": node["unique_id"],
                    "path": node["path"],
                    "type": list(node.labels)[0],
                    "label": node.get("title", ""),
                    "data": converted_data
                }
            }

    except Exception as e:
        logger.error(f"Error getting default node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))