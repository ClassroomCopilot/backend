from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
from modules.database.tools.neontology.graphconnection import GraphConnection, init_neontology
from modules.database.tools.neontology.basenode import BaseNode
from modules.database.tools.neontology.baserelationship import BaseRelationship
from typing import Optional, Dict, Any, List
from neo4j import Record as Neo4jRecord
import re

log_name = 'api_modules_database_neo4j_utils_neontology'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

class NeontologyProvider:
    """Provider class for managing Neontology connections and operations."""
    
    def __init__(self):
        """Initialize the provider with Neo4j connection details from environment."""
        self.host = os.getenv("HOST_NEO4J")
        self.port = os.getenv("PORT_NEO4J_BOLT")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.connection = None
        self.current_database = None
        
    def _validate_database_name(self, database: str) -> str:
        """Validate and format database name to handle special characters."""
        if not database:
            raise ValueError("Database name cannot be empty")
            
        if not re.match(r'^[a-zA-Z0-9_\.]+$', database):
            raise ValueError("Database name contains invalid characters")
            
        if database.count('.') > 1:
            parts = database.split('.')
            if len(parts) > 2:
                formatted_name = f"{parts[0]}.{'.'.join(parts[1:])}"
                logging.info(f"Reformatted database name from {database} to {formatted_name}")
                return formatted_name
                
        return database
        
    def connect(self, database: str = 'neo4j') -> None:
        """Establish connection to Neo4j using Neontology."""
        try:
            formatted_database = self._validate_database_name(database)
            
            if self.current_database != formatted_database and self.connection is not None:
                self.close()
            
            if self.connection is None:
                init_neontology(
                    neo4j_uri=f"bolt://{self.host}:{self.port}",
                    neo4j_username=self.user,
                    neo4j_password=self.password
                )
                self.connection = GraphConnection()
                self.current_database = formatted_database
                logging.info(f"Neontology connection initialized with host: {self.host}, port: {self.port}, database: {formatted_database}")
            
        except Exception as e:
            logging.error(f"Failed to initialize Neontology connection: {str(e)}")
            raise

    def list_databases(self) -> List[str]:
        """List all available Neo4j databases."""
        try:
            with self.connection.driver.session() as session:
                result = session.run("SHOW DATABASES")
                return [record["name"] for record in result]
        except Exception as e:
            logging.error(f"Error listing databases: {str(e)}")
            raise

    def check_database_exists(self, database_name: str) -> bool:
        """Check if a specific database exists."""
        try:
            databases = self.list_databases()
            return database_name in databases
        except Exception as e:
            logging.error(f"Error checking database existence: {str(e)}")
            return False

    def create_database(self, database_name: str) -> None:
        """Create a new Neo4j database."""
        try:
            formatted_name = self._validate_database_name(database_name)
            with self.connection.driver.session() as session:
                session.run(f"CREATE DATABASE {formatted_name} IF NOT EXISTS")
                logging.info(f"Created database: {formatted_name}")
        except Exception as e:
            logging.error(f"Error creating database: {str(e)}")
            raise
            
    def reset_connection(self) -> None:
        """Reset the connection, forcing a new one to be created on next use."""
        if self.connection:
            self.close()
            
    def create_or_merge_node(self, node: BaseNode, database: str = 'neo4j', operation: str = "merge") -> None:
        """Create or merge a node in the Neo4j database."""
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
                
            if operation == "create":
                node.create(database=database)
            elif operation == "merge":
                node.merge(database=database)
            else:
                logging.error(f"Invalid operation: {operation}")
                raise ValueError(f"Invalid operation: {operation}")
        except Exception as e:
            logging.error(f"Error in processing node: {e}")
            raise
            
    def create_or_merge_relationship(self, relationship: BaseRelationship, database: str = 'neo4j', operation: str = "merge") -> None:
        """Create or merge a relationship in the Neo4j database."""
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
                
            if operation == "create":
                relationship.create(database=database)
            elif operation == "merge":
                relationship.merge(database=database)
            else:
                logging.error(f"Invalid operation: {operation}")
                raise ValueError(f"Invalid operation: {operation}")
        except Exception as e:
            logging.error(f"Error in processing relationship: {e}")
            raise
            
    def cypher_write(self, cypher: str, params: Dict[str, Any] = {}, database: str = 'neo4j') -> None:
        """Execute a write transaction."""
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
            self.connection.cypher_write(cypher, params)
        except Exception as e:
            logging.error(f"Error in cypher write: {e}")
            raise
            
    def cypher_read(self, cypher: str, params: Dict[str, Any] = {}, database: str = 'neo4j') -> Optional[Neo4jRecord]:
        """Execute a read transaction returning a single record."""
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
            return self.connection.cypher_read(cypher, params)
        except Exception as e:
            logging.error(f"Error in cypher read: {e}")
            raise
            
    def cypher_read_many(self, cypher: str, params: Dict[str, Any] = {}, database: str = 'neo4j') -> List[Neo4jRecord]:
        """Execute a read transaction returning multiple records."""
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
            return self.connection.cypher_read_many(cypher, params)
        except Exception as e:
            logging.error(f"Error in cypher read many: {e}")
            raise
            
    def run_query(self, cypher: str, params: Dict[str, Any] = {}, database: str = 'neo4j') -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dictionaries.
        This is a convenience method that handles both single and multiple record results.
        
        Args:
            cypher: The Cypher query to execute
            params: Query parameters
            database: Target database name
            
        Returns:
            List[Dict[str, Any]]: Query results as a list of dictionaries
        """
        try:
            if not self.connection or self.current_database != database:
                self.connect(database)
                
            # Use cypher_read_many for consistent return type
            records = self.connection.cypher_read_many(cypher, params)
            
            # Convert Neo4j records to dictionaries
            results = []
            for record in records:
                # Handle both Record and dict types
                if isinstance(record, Neo4jRecord):
                    results.append(dict(record))
                else:
                    results.append(record)
                    
            return results
            
        except Exception as e:
            logging.error(f"Error in run_query: {e}")
            raise
            
    def close(self) -> None:
        """Close the Neontology connection."""
        if self.connection:
            # The connection will be closed when the GraphConnection instance is deleted
            self.connection = None
            self.current_database = None
            logging.info("Neontology connection closed")
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
