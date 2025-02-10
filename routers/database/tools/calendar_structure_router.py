import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from modules.logger_tool import initialise_logger
from modules.database.tools import neo4j_driver_tools as driver_tools

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
router = APIRouter()

@router.get("/get-calendar-structure")
async def get_calendar_structure(db_name: str) -> Dict[str, Any]:
    """
    Get the complete calendar structure including years, months, weeks, and days.
    """
    try:
        # Get all calendar nodes in a single query
        query = """
        // Match all calendar-related nodes
        MATCH (y:CalendarYear)
        OPTIONAL MATCH (y)-[:YEAR_INCLUDES_MONTH]->(m:CalendarMonth)
        OPTIONAL MATCH (m)-[:MONTH_INCLUDES_DAY]->(d:CalendarDay)
        OPTIONAL MATCH (w:CalendarWeek)-[:WEEK_INCLUDES_DAY]->(d)
        WITH y, m, w, d
        ORDER BY y.date, m.date, w.date, d.date

        // Collect all nodes with dates converted to strings
        RETURN {
            years: collect(DISTINCT {
                id: y.unique_id,
                path: y.path,
                date: toString(y.date),
                __primarylabel__: 'CalendarYear'
            }),
            months: collect(DISTINCT {
                id: m.unique_id,
                path: m.path,
                date: toString(m.date),
                __primarylabel__: 'CalendarMonth'
            }),
            weeks: collect(DISTINCT {
                id: w.unique_id,
                path: w.path,
                date: toString(w.date),
                __primarylabel__: 'CalendarWeek'
            }),
            days: collect(DISTINCT {
                id: d.unique_id,
                path: d.path,
                date: toString(d.date),
                week_id: w.unique_id,
                month_id: m.unique_id,
                __primarylabel__: 'CalendarDay'
            })
        } as structure
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Calendar structure not found")
            
            structure = record["structure"]
            
            # Find current day using string comparison
            today = datetime.now().strftime("%Y-%m-%d")
            current_day = next(
                (day["id"] for day in structure["days"] 
                 if day["date"] == today),
                structure["days"][0]["id"] if structure["days"] else None
            )

            return {
                "status": "success",
                "structure": {
                    "years": structure["years"],
                    "months": structure["months"],
                    "weeks": structure["weeks"],
                    "days": structure["days"],
                    "currentDay": current_day
                }
            }

    except Exception as e:
        logger.error(f"Error getting calendar structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-calendar-days")
async def get_calendar_days(db_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Get all calendar days in a date range.
    """
    try:
        query = """
        MATCH (d:CalendarDay)
        WHERE date(d.date) >= date($start_date) AND date(d.date) <= date($end_date)
        OPTIONAL MATCH (w:CalendarWeek)-[:WEEK_INCLUDES_DAY]->(d)
        OPTIONAL MATCH (m:CalendarMonth)-[:MONTH_INCLUDES_DAY]->(d)
        RETURN {
            id: d.unique_id,
            path: d.path,
            date: d.date,
            week_id: w.unique_id,
            month_id: m.unique_id,
            __primarylabel__: 'CalendarDay'
        } as day
        ORDER BY d.date
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, start_date=start_date, end_date=end_date)
            days = [record["day"] for record in result]

            return {
                "status": "success",
                "days": days
            }

    except Exception as e:
        logger.error(f"Error getting calendar days: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-calendar-weeks")
async def get_calendar_weeks(db_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Get all calendar weeks in a date range.
    """
    try:
        query = """
        MATCH (w:CalendarWeek)-[:WEEK_INCLUDES_DAY]->(d:CalendarDay)
        WHERE date(w.date) >= date($start_date) AND date(w.date) <= date($end_date)
        WITH w, collect(d) as days
        RETURN {
            id: w.unique_id,
            path: w.path,
            date: w.date,
            day_ids: [day in days | day.unique_id],
            __primarylabel__: 'CalendarWeek'
        } as week
        ORDER BY w.date
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, start_date=start_date, end_date=end_date)
            weeks = [record["week"] for record in result]

            return {
                "status": "success",
                "weeks": weeks
            }

    except Exception as e:
        logger.error(f"Error getting calendar weeks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-calendar-months")
async def get_calendar_months(db_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Get all calendar months in a date range.
    """
    try:
        query = """
        MATCH (m:CalendarMonth)-[:MONTH_INCLUDES_DAY]->(d:CalendarDay)
        WHERE date(m.date) >= date($start_date) AND date(m.date) <= date($end_date)
        WITH m, collect(d) as days
        RETURN {
            id: m.unique_id,
            path: m.path,
            date: m.date,
            day_ids: [day in days | day.unique_id],
            __primarylabel__: 'CalendarMonth'
        } as month
        ORDER BY m.date
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query, start_date=start_date, end_date=end_date)
            months = [record["month"] for record in result]

            return {
                "status": "success",
                "months": months
            }

    except Exception as e:
        logger.error(f"Error getting calendar months: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-calendar-years")
async def get_calendar_years(db_name: str) -> Dict[str, Any]:
    """
    Get all calendar years.
    """
    try:
        query = """
        MATCH (y:CalendarYear)-[:YEAR_INCLUDES_MONTH]->(m:CalendarMonth)
        WITH y, collect(m) as months
        RETURN {
            id: y.unique_id,
            path: y.path,
            date: y.date,
            month_ids: [month in months | month.unique_id],
            __primarylabel__: 'CalendarYear'
        } as year
        ORDER BY y.date
        """

        with driver_tools.get_session(database=db_name) as session:
            result = session.run(query)
            years = [record["year"] for record in result]

            return {
                "status": "success",
                "years": years
            }

    except Exception as e:
        logger.error(f"Error getting calendar years: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 