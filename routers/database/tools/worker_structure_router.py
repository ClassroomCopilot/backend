import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from modules.logger_tool import initialise_logger
from modules.database.tools import neo4j_driver_tools as driver_tools

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
router = APIRouter()

@router.get("/get-worker-structure")
async def get_worker_structure(db_name: str) -> Dict[str, Any]:
    """
    Get the complete worker structure including timetables, classes, lessons, journals, and planners.
    """
    try:
        # Get all worker-related nodes in a single query
        query = """
        // Match all worker-related nodes
        MATCH (t:Teacher)
        OPTIONAL MATCH (t)-[:TEACHER_HAS_TIMETABLE]->(tt:UserTeacherTimetable)
        OPTIONAL MATCH (t)-[:TEACHER_HAS_CLASS]->(c:Class)
        OPTIONAL MATCH (t)-[:TEACHER_HAS_LESSON]->(l:TimetableLesson)
        OPTIONAL MATCH (t)-[:TEACHER_HAS_JOURNAL]->(j:Journal)
        OPTIONAL MATCH (t)-[:TEACHER_HAS_PLANNER]->(p:Planner)
        WITH t, tt, c, l, j, p
        ORDER BY tt.start_date, c.created, l.created, j.created, p.created

        // Collect all nodes
        RETURN {
            timetables: collect(DISTINCT {
                id: tt.unique_id,
                path: tt.path,
                title: tt.title,
                type: tt.__primarylabel__,
                startTime: toString(tt.start_date),
                endTime: toString(tt.end_date)
            }),
            classes: collect(DISTINCT {
                id: c.unique_id,
                path: c.path,
                title: c.title,
                type: c.__primarylabel__
            }),
            lessons: collect(DISTINCT {
                id: l.unique_id,
                path: l.path,
                title: l.title,
                type: l.__primarylabel__
            }),
            journals: collect(DISTINCT {
                id: j.unique_id,
                path: j.path,
                title: j.title,
                type: j.__primarylabel__
            }),
            planners: collect(DISTINCT {
                id: p.unique_id,
                path: p.path,
                title: p.title,
                type: p.__primarylabel__
            })
        } as structure
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Worker structure not found")
            
            structure = record["structure"]
            
            return {
                "status": "success",
                "data": {
                    "timetables": {
                        "default": structure["timetables"]
                    },
                    "classes": {
                        "default": structure["classes"]
                    },
                    "lessons": {
                        "default": structure["lessons"]
                    },
                    "journals": {
                        "default": structure["journals"]
                    },
                    "planners": {
                        "default": structure["planners"]
                    }
                }
            }

    except Exception as e:
        logger.error(f"Error getting worker structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-timetables")
async def get_timetables(db_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Get all timetables in a date range.
    """
    try:
        query = """
        MATCH (tt:UserTeacherTimetable)
        WHERE date(tt.start_date) >= date($start_date) AND date(tt.end_date) <= date($end_date)
        RETURN {
            id: tt.unique_id,
            path: tt.path,
            title: tt.title,
            type: tt.__primarylabel__,
            startTime: toString(tt.start_date),
            endTime: toString(tt.end_date)
        } as timetable
        ORDER BY tt.start_date
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, start_date=start_date, end_date=end_date)
            timetables = [record["timetable"] for record in result]

            return {
                "status": "success",
                "timetables": timetables
            }

    except Exception as e:
        logger.error(f"Error getting timetables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-journals")
async def get_journals(db_name: str) -> Dict[str, Any]:
    """
    Get all journals.
    """
    try:
        query = """
        MATCH (j:Journal)
        RETURN {
            id: j.unique_id,
            path: j.path,
            title: j.title,
            type: j.__primarylabel__
        } as journal
        ORDER BY j.created
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            journals = [record["journal"] for record in result]

            return {
                "status": "success",
                "journals": journals
            }

    except Exception as e:
        logger.error(f"Error getting journals: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-planners")
async def get_planners(db_name: str) -> Dict[str, Any]:
    """
    Get all planners.
    """
    try:
        query = """
        MATCH (p:Planner)
        RETURN {
            id: p.unique_id,
            path: p.path,
            title: p.title,
            type: p.__primarylabel__
        } as planner
        ORDER BY p.created
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            planners = [record["planner"] for record in result]

            return {
                "status": "success",
                "planners": planners
            }

    except Exception as e:
        logger.error(f"Error getting planners: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
