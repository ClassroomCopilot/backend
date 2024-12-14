import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(
    log_name='api_main_fastapi',
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_dir=os.getenv("LOG_PATH", "/logs"),
    log_format='default',
    runtime=True
)
from fastapi import FastAPI
import yaml
import time

import modules.database.init.init_school as init_school
import modules.database.init.init_school_timetable as init_school_timetable
import modules.database.init.init_curriculum as init_curriculum
import modules.database.init.xl_tools as xl
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
from modules.database.schemas.entity_neo import SchoolNode
import modules.database.tools.filesystem_tools as fs_tools

dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
def get_cors_origins():
    """Get CORS origins based on environment configuration"""
    return [
        f"http://{os.getenv('HOST_FRONTEND')}:{os.getenv('PORT_FRONTEND')}",
        f"http://{os.getenv('HOST_NEO4J')}:{os.getenv('PORT_NEO4J_HTTP')}",
        f"https://{os.getenv('SITE_URL')}",
    ]

def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware for the FastAPI application"""
    from fastapi.middleware.cors import CORSMiddleware
    origins = get_cors_origins()
    logger.debug(f"Setting up CORS with origins: {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

def initialize_application():
    """Initialize all application components if INIT_RUN is True and set INIT_RUN to False"""
    if os.getenv("INIT_RUN", "false").lower() == "true":
        logger.debug("Starting application initialization")
        try:
            initialize_databases()
            create_tldraw_multiplayer_filesystem()
            logger.warning("Setting INIT_RUN to false in current environment only. Manual modification of the .env file required to persist this change.")
            os.environ["INIT_RUN"] = "false"
            logger.success("Application initialization completed successfully")
        except Exception as e:
            logger.error(f"Error during application initialization: {str(e)}")
            raise

def initialize_databases():
    """Initialize the databases"""
    logger.debug("Initializing databases")

    # Get the driver
    driver = driver_tools.get_driver()
    
    if driver is None:
        logger.error("Failed to connect to Neo4j")
        return
    
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    
    try:
        with driver.session() as session:
            for db_name in config["databases"]["initial_databases"]:
                session_tools.create_database(session, db_name)
        driver_tools.close_driver(driver)
        time.sleep(5)
        initialise_school_at_startup(config["school"]["kevlarai"])
    except Exception as e:
        logger.error(f"Error initializing databases: {str(e)}")
    finally:
        logger.info("Databases initialization completed")

def initialise_school_at_startup(school_config: dict):
        """Initialize a school with the provided configuration
        
        Args:
            school_config (dict): Dictionary containing school configuration with keys:
                - school_uuid: Unique identifier for the school
                - school_name: Name of the school
                - school_website: School's website URL
                - timetable_file: Path to Excel file containing timetable data
                - curriculum_file: Path to Excel file containing curriculum data
        """
        db_name = f"cc.ccschools.{school_config['school_uuid']}"
        
        logger.info(f"Creating database for {school_config['school_name']} using db_name: {db_name}")
        driver = driver_tools.get_driver()
        if driver is None:
            logger.error("Failed to connect to Neo4j")
            return
        
        with driver.session() as session:
            session_tools.create_database(session, db_name)
            logger.debug(f"Database {db_name} created")
        
        # Add filesystem path debugging
        base_path = os.getenv("NODE_FILESYSTEM_PATH")
        schools_path = os.path.join(base_path, "schools")
        school_path = os.path.join(schools_path, f"cc.ccschools.{school_config['school_uuid']}")
        
        logger.debug("Filesystem paths:", {
            "base_path": base_path,
            "schools_path": schools_path,
            "school_path": school_path
        })
        
        # Check if directories exist
        logger.debug("Directory existence check:", {
            "base_exists": os.path.exists(base_path),
            "schools_exists": os.path.exists(schools_path),
            "school_exists": os.path.exists(school_path)
        })
        
        # Create database entry for school without timetable or curriculum
        logger.info(f"Creating school entry for {school_config['school_name']} in database {db_name} without timetable or curriculum")
        result = init_school.create_school(
            db_name=db_name,
            school_uuid=school_config["school_uuid"],
            school_name=school_config["school_name"],
            school_website=school_config["school_website"]
        )
        logger.success(f"{school_config['school_name']} school entry created successfully")
        
        # Create school node from result
        school_node = result['school_node']
        refreshed_school_node = SchoolNode(
            unique_id=school_node.unique_id,
            school_uuid=school_node.school_uuid,
            school_name=school_node.school_name,
            school_website=school_node.school_website,
            path=school_node.path
        )

        # Create timetable entries for school from Excel file
        timetable_file = os.path.join(os.getenv("BACKEND_INIT_PATH"), school_config["timetable_file"])
        
        logger.info(f"Creating timetable entries for {school_config['school_name']} using timetable file: {timetable_file}.")
        school_timetable_dataframes = xl.create_dataframes(timetable_file)
        
        init_school_timetable.create_school_timetable(
            dataframes=school_timetable_dataframes, 
            db_name=db_name, 
            school_node=refreshed_school_node
        )
        logger.success("Timetable entries created successfully")

        # Create curriculum entries for school from Excel file
        curriculum_file = os.path.join(os.getenv("BACKEND_INIT_PATH"), school_config["curriculum_file"])
        
        school_curriculum_dataframes = xl.create_dataframes(curriculum_file)
        
        logger.info(f"Creating curriculum entries for {school_config['school_name']} using curriculum file: {curriculum_file}.")
        init_curriculum.create_curriculum(
            dataframes=school_curriculum_dataframes, 
            db_name=db_name, 
            school_node=refreshed_school_node
        )
        logger.success("Curriculum entries created successfully")

def create_tldraw_multiplayer_filesystem():
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
    
    if dev_mode:
        fs = fs_tools.ClassroomCopilotFilesystem(os.path.join(os.getenv("NODE_FILESYSTEM_PATH"), "multiplayer")) # TODO: Will change when we implement multiplayer fully.
        logger.info("Creating tldraw multiplayer filesystem with dev mode")
    else:
        logger.error("Warning, we need to implement production mode for tldraw filesystem")
        return

    fs.initialise_tldraw_file_system()
    logger.success("tldraw filesystem created successfully")

def populate_ukschools_database():
    # TODO: Populate the uk schools database, cc.ukschools, with the UK school data
    pass
