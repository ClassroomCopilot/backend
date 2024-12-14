from fastapi import APIRouter, Depends
from backend.app.run.dependencies import admin_dependency

import modules.database.tools.neo4j_driver_tools as driver
import modules.database.tools.neo4j_session_tools as session
import modules.database.tools.neo4j_http_tools as http
import modules.database.tools.queries as query

router = APIRouter()

# Handle neo4j driver
@router.post("/create-driver")
async def create_driver(driver: driver.Neo4jDriver = Depends(driver.get_neo4j_driver)):
    return driver