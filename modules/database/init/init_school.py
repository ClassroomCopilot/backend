import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("BACKEND_LOG_PATH"), 'default', True)
import modules.database.schemas.entity_neo as entity_neo
import modules.database.init.init_school_timetable as init_school_timetable
import modules.database.tools.neontology_tools as neon
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem

def create_school(db_name: str, school_uuid: str, school_name: str, school_website: str, dataframes=None):
    if not school_name or not school_uuid or not school_website:
        logger.error("School name, school_uuid and school_website are required to create a school.")
        raise ValueError("School name, school_uuid and school_website are required to create a school.")
    
    logger.info(f"Initialising neo4j connection...")
    neon.init_neontology_connection()
    
    # Initialize the filesystem handler
    logger.info(f"Initialising filesystem handler...")
    fs_handler = ClassroomCopilotFilesystem(db_name, init_run_type="school")
    
    logger.info(f"Creating school directory...")
    _, school_path = fs_handler.create_school_directory(school_uuid=None) # TODO: Manage this better.

    # Create School Node
    school_node = entity_neo.SchoolNode(
        unique_id=f'School_{school_uuid}',
        school_uuid=school_uuid,
        school_name=school_name,
        school_website=school_website,
        path=school_path
    )
    logger.info(f"Creating default tldraw file...")
    fs_handler.create_default_tldraw_file(school_path, school_node.to_dict())
    
    logger.info(f"Creating school node...")
    neon.create_or_merge_neontology_node(school_node, database=db_name, operation='merge')
    
    school_nodes = {
        'school_node': school_node,
        'db_name': db_name
    }
    
    if dataframes is not None:
        logger.info(f"Creating school timetable for {school_name} with {len(dataframes)} dataframes...")
        school_timetable_nodes = init_school_timetable.create_school_timetable(dataframes, db_name, school_node)
        school_nodes['school_timetable_nodes'] = school_timetable_nodes
    else:
        logger.warning(f"No dataframes provided for {school_name}, skipping school timetable...")
    
    logger.info(f"School {school_name} created successfully...")
    return school_nodes
