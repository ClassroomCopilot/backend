from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_langchain_graph_qa'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase

router = APIRouter()

@router.get("/graph-data")
async def get_graph_data():
    uri = f"neo4j+s://{os.environ.get('HOST_NEO4J', '')}:{os.environ.get('NEO4J_BOLT_PORT', '')}"
    user = os.environ.get("NEO4J_USER", "")
    password = os.environ.get("NEO4J_PASSWORD", "")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    query = """
    MATCH (ksn:KeyStageSyllabusNode)-[r]-(connectedNode)
    RETURN ksn, r, connectedNode
    """
    with driver.session() as session:
        result = session.run(query)
        data = [{"ksn": record["ksn"], "relationship": record["r"], "connectedNode": record["connectedNode"]} for record in result]
    return data