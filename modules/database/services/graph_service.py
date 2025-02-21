import os
from typing import Dict, Any
from modules.logger_tool import initialise_logger
import modules.database.tools.neo4j_driver_tools as driver_tools
from modules.database.admin.neontology_provider import NeontologyProvider
from modules.database.admin.graph_provider import GraphNamingProvider

class GraphService:
    def __init__(self):
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        self.driver = driver_tools.get_driver()
        self.neontology = NeontologyProvider()
        self.graph_naming = GraphNamingProvider()

    def check_schema_status(self, database_name: str = "neo4j") -> Dict[str, Any]:
        """Check the status of Neo4j schema including constraints, indexes, and labels"""
        try:
            with self.driver.session(database=database_name) as session:
                # Check constraints
                constraints_result = session.run("SHOW CONSTRAINTS")
                constraints = list(constraints_result)
                
                # Check indexes
                indexes_result = session.run("SHOW INDEXES")
                indexes = list(indexes_result)
                
                # Check labels
                labels_result = session.run("CALL db.labels()")
                labels = list(labels_result)
                
                return {
                    "constraints_count": len(constraints),
                    "indexes_count": len(indexes),
                    "labels_count": len(labels),
                    "constraints": [dict(record) for record in constraints],
                    "indexes": [dict(record) for record in indexes],
                    "labels": [dict(record) for record in labels]
                }
        except Exception as e:
            self.logger.error(f"Error checking schema status: {str(e)}")
            return {
                "constraints_count": 0,
                "indexes_count": 0,
                "labels_count": 0,
                "error": str(e)
            }

    def initialize_schema(self, database_name: str = "neo4j") -> Dict[str, Any]:
        """Initialize Neo4j schema with required constraints and indexes"""
        try:
            schema_queries = self.graph_naming.get_schema_creation_queries()
            
            with self.driver.session(database=database_name) as session:
                for query in schema_queries:
                    session.run(query)
                
                return {
                    "status": "success",
                    "message": "Schema initialized successfully",
                    "details": self.check_schema_status(database_name)
                }
        except Exception as e:
            self.logger.error(f"Error initializing schema: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
