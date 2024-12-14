from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_neo4j_driver_tools'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import time
from neo4j import GraphDatabase as gd

def get_driver(db_name=None, url=None, auth=None):
    if url is None:
        host = os.getenv("HOST_NEO4J")
        port = os.getenv("PORT_NEO4J_BOLT")
        url = f"bolt://{host}:{port}"
        auth = (os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    
    driver = None
    connection_attempts = 0
    while driver is None:
        connection_attempts += 1
        try:
            logging.info(f"Attempting to connect to Neo4j at {url}")
            driver = gd.driver(url, auth=auth)
            driver.verify_connectivity()
            logging.info(f"Connected to Neo4j at {url}")
        except Exception as e:
            logging.error(f"Connection attempt {connection_attempts} failed: {e}")
            if connection_attempts >= 3:
                return None
            # time.sleep(10)
    
    # Test the connection with the specific database
    if db_name:
        try:
            with driver.session(database=db_name) as session:
                result = session.run("RETURN 'Connection successful' AS message")
                message = result.single()["message"]
                logging.info(f"Connection to Neo4j at {url} with database {db_name} successful")
        except Exception as e:
            logging.error(f"Failed to connect to the database {db_name}: {e}")
            driver.close()
            return None

    return driver

def close_driver(driver):
    logging.info(f"Closing driver")
    driver.close()