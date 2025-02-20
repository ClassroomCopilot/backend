from enum import Enum
from typing import Optional, List, Dict, Any
import logging

from modules.database.admin.neontology_provider import NeontologyProvider

class NodeLabels(Enum):
    SCHOOL = "School"
    DEPARTMENT_STRUCTURE = "DepartmentStructure"
    CURRICULUM_STRUCTURE = "CurriculumStructure"
    PASTORAL_STRUCTURE = "PastoralStructure"
    DEPARTMENT = "Department"
    KEY_STAGE = "KeyStage"
    YEAR_GROUP = "YearGroup"

class RelationshipTypes(Enum):
    HAS_DEPARTMENT_STRUCTURE = "HAS_DEPARTMENT_STRUCTURE"
    HAS_CURRICULUM_STRUCTURE = "HAS_CURRICULUM_STRUCTURE"
    HAS_PASTORAL_STRUCTURE = "HAS_PASTORAL_STRUCTURE"
    HAS_DEPARTMENT = "HAS_DEPARTMENT"
    INCLUDES_KEY_STAGE = "INCLUDES_KEY_STAGE"
    INCLUDES_YEAR_GROUP = "INCLUDES_YEAR_GROUP"

class PropertyKeys(Enum):
    UNIQUE_ID = "unique_id"
    PATH = "path"
    URN = "urn"
    ESTABLISHMENT_NUMBER = "establishment_number"
    ESTABLISHMENT_NAME = "establishment_name"
    ESTABLISHMENT_TYPE = "establishment_type"
    ESTABLISHMENT_STATUS = "establishment_status"
    PHASE_OF_EDUCATION = "phase_of_education"
    STATUTORY_LOW_AGE = "statutory_low_age"
    STATUTORY_HIGH_AGE = "statutory_high_age"
    RELIGIOUS_CHARACTER = "religious_character"
    SCHOOL_CAPACITY = "school_capacity"
    SCHOOL_WEBSITE = "school_website"
    OFSTED_RATING = "ofsted_rating"
    DEPARTMENT_NAME = "department_name"
    KEY_STAGE = "key_stage"
    KEY_STAGE_NAME = "key_stage_name"
    YEAR_GROUP = "year_group"
    YEAR_GROUP_NAME = "year_group_name"
    CREATED = "created"
    MERGED = "merged"

class SchemaDefinition:
    """Class to hold schema definition queries and information"""
    
    @staticmethod
    def get_schema_info() -> Dict[str, List[Dict]]:
        """Returns a dictionary containing the schema definition for nodes and relationships."""
        return {
            "nodes": [
                {
                    "label": "School",
                    "description": "Represents a school entity",
                    "required_properties": ["unique_id", "urn", "name"],
                    "optional_properties": ["address", "postcode", "phone", "email", "website"]
                },
                {
                    "label": "DepartmentStructure",
                    "description": "Represents the department structure of a school",
                    "required_properties": ["unique_id", "name"],
                    "optional_properties": ["description", "head_of_department"]
                },
                {
                    "label": "CurriculumStructure",
                    "description": "Represents the curriculum structure of a school",
                    "required_properties": ["unique_id", "name"],
                    "optional_properties": ["description", "key_stage", "subject"]
                },
                {
                    "label": "PastoralStructure",
                    "description": "Represents the pastoral structure of a school",
                    "required_properties": ["unique_id", "name"],
                    "optional_properties": ["description", "year_group", "form_group"]
                }
            ],
            "relationships": [
                {
                    "type": "HAS_DEPARTMENT_STRUCTURE",
                    "description": "Links a school to its department structure",
                    "source": "School",
                    "target": "DepartmentStructure",
                    "properties": ["created_at"]
                },
                {
                    "type": "HAS_CURRICULUM_STRUCTURE",
                    "description": "Links a school to its curriculum structure",
                    "source": "School",
                    "target": "CurriculumStructure",
                    "properties": ["created_at"]
                },
                {
                    "type": "HAS_PASTORAL_STRUCTURE",
                    "description": "Links a school to its pastoral structure",
                    "source": "School",
                    "target": "PastoralStructure",
                    "properties": ["created_at"]
                }
            ]
        }
    
    @staticmethod
    def get_schema_creation_queries() -> List[str]:
        """Returns a list of Cypher queries to create the schema."""
        return [
            # Node Uniqueness Constraints
            f"CREATE CONSTRAINT school_unique_id IF NOT EXISTS FOR (n:{NodeLabels.SCHOOL.value}) REQUIRE n.{PropertyKeys.UNIQUE_ID.value} IS UNIQUE",
            f"CREATE CONSTRAINT department_unique_id IF NOT EXISTS FOR (n:{NodeLabels.DEPARTMENT_STRUCTURE.value}) REQUIRE n.{PropertyKeys.UNIQUE_ID.value} IS UNIQUE",
            f"CREATE CONSTRAINT curriculum_unique_id IF NOT EXISTS FOR (n:{NodeLabels.CURRICULUM_STRUCTURE.value}) REQUIRE n.{PropertyKeys.UNIQUE_ID.value} IS UNIQUE",
            f"CREATE CONSTRAINT pastoral_unique_id IF NOT EXISTS FOR (n:{NodeLabels.PASTORAL_STRUCTURE.value}) REQUIRE n.{PropertyKeys.UNIQUE_ID.value} IS UNIQUE",
            
            # Indexes for Performance
            f"CREATE INDEX school_urn IF NOT EXISTS FOR (n:{NodeLabels.SCHOOL.value}) ON (n.{PropertyKeys.URN.value})",
            f"CREATE INDEX school_name IF NOT EXISTS FOR (n:{NodeLabels.SCHOOL.value}) ON (n.{PropertyKeys.ESTABLISHMENT_NAME.value})",
            f"CREATE INDEX department_name IF NOT EXISTS FOR (n:{NodeLabels.DEPARTMENT_STRUCTURE.value}) ON (n.{PropertyKeys.DEPARTMENT_NAME.value})",
            f"CREATE INDEX curriculum_name IF NOT EXISTS FOR (n:{NodeLabels.CURRICULUM_STRUCTURE.value}) ON (n.name)",
            f"CREATE INDEX pastoral_name IF NOT EXISTS FOR (n:{NodeLabels.PASTORAL_STRUCTURE.value}) ON (n.name)",
        ]
    
    @staticmethod
    def get_schema_verification_queries() -> Dict[str, str]:
        """Returns a dictionary of queries to verify the schema state."""
        return {
            "constraints": "SHOW CONSTRAINTS",
            "indexes": "SHOW INDEXES",
            "labels": "CALL db.labels()"
        }

class GraphNamingProvider:
    @staticmethod
    def get_school_unique_id(urn: str) -> str:
        """Generate unique ID for a school node."""
        return f"School_{urn}"

    @staticmethod
    def get_department_structure_unique_id(school_unique_id: str) -> str:
        """Generate unique ID for a department structure node."""
        return f"DepartmentStructure_{school_unique_id}"

    @staticmethod
    def get_curriculum_structure_unique_id(school_unique_id: str) -> str:
        """Generate unique ID for a curriculum structure node."""
        return f"CurriculumStructure_{school_unique_id}"

    @staticmethod
    def get_pastoral_structure_unique_id(school_unique_id: str) -> str:
        """Generate unique ID for a pastoral structure node."""
        return f"PastoralStructure_{school_unique_id}"

    @staticmethod
    def get_department_unique_id(school_unique_id: str, department_name: str) -> str:
        """Generate unique ID for a department node."""
        return f"Department_{school_unique_id}_{department_name.replace(' ', '_')}"

    @staticmethod
    def get_key_stage_unique_id(curriculum_structure_unique_id: str, key_stage: str) -> str:
        """Generate unique ID for a key stage node."""
        return f"KeyStage_{curriculum_structure_unique_id}_KStg{key_stage}"

    @staticmethod
    def get_year_group_unique_id(school_unique_id: str, year_group: int) -> str:
        """Generate unique ID for a year group node."""
        return f"YearGroup_{school_unique_id}_YGrp{year_group}"

    @staticmethod
    def get_school_path(database_name: str, urn: str) -> str:
        """Generate path for a school node."""
        return f"/schools/{database_name}/{urn}"

    @staticmethod
    def get_department_path(school_path: str, department_name: str) -> str:
        """Generate path for a department node."""
        return f"{school_path}/departments/{department_name}"

    @staticmethod
    def get_department_structure_path(school_path: str) -> str:
        """Generate path for a department structure node."""
        return f"{school_path}/departments"

    @staticmethod
    def get_curriculum_path(school_path: str) -> str:
        """Generate path for a curriculum structure node."""
        return f"{school_path}/curriculum"

    @staticmethod
    def get_pastoral_path(school_path: str) -> str:
        """Generate path for a pastoral structure node."""
        return f"{school_path}/pastoral"

    @staticmethod
    def get_key_stage_path(curriculum_path: str, key_stage: str) -> str:
        """Generate path for a key stage node."""
        return f"{curriculum_path}/key_stage_{key_stage}"

    @staticmethod
    def get_year_group_path(pastoral_path: str, year_group: int) -> str:
        """Generate path for a year group node."""
        return f"{pastoral_path}/year_{year_group}"

    @staticmethod
    def get_cypher_match_school(unique_id: str) -> str:
        """Generate Cypher MATCH clause for finding a school node."""
        return f"MATCH (s:{NodeLabels.SCHOOL.value} {{{PropertyKeys.UNIQUE_ID.value}: $school_id}})"

    @staticmethod
    def get_cypher_check_basic_structure() -> str:
        """Generate Cypher query for checking basic structure existence and validity."""
        return """
            // Find the school node
            MATCH (s:{school})
            
            // Check for department structure with any relationship
            OPTIONAL MATCH (s)-[r1]-(dept_struct:{dept_struct})
            
            // Check for curriculum structure with any relationship
            OPTIONAL MATCH (s)-[r2]-(curr_struct:{curr_struct})
            
            // Check for pastoral structure with any relationship
            OPTIONAL MATCH (s)-[r3]-(past_struct:{past_struct})
            
            // Return structure information
            RETURN {{
                has_basic: 
                    dept_struct IS NOT NULL AND r1 IS NOT NULL AND
                    curr_struct IS NOT NULL AND r2 IS NOT NULL AND
                    past_struct IS NOT NULL AND r3 IS NOT NULL,
                department_structure: {{
                    exists: dept_struct IS NOT NULL AND r1 IS NOT NULL
                }},
                curriculum_structure: {{
                    exists: curr_struct IS NOT NULL AND r2 IS NOT NULL
                }},
                pastoral_structure: {{
                    exists: past_struct IS NOT NULL AND r3 IS NOT NULL
                }}
            }} as status
        """.format(
            school=NodeLabels.SCHOOL.value,
            dept_struct=NodeLabels.DEPARTMENT_STRUCTURE.value,
            curr_struct=NodeLabels.CURRICULUM_STRUCTURE.value,
            past_struct=NodeLabels.PASTORAL_STRUCTURE.value
        )

    @staticmethod
    def get_cypher_check_detailed_structure() -> str:
        """Generate Cypher query for checking detailed structure existence and validity."""
        return """
            // Find the school node
            MATCH (s:{school} {{unique_id: $school_id}})
            
            // Check for department structure and departments
            OPTIONAL MATCH (s)-[r1]-(dept_struct:{dept_struct})
            WHERE dept_struct.unique_id = 'DepartmentStructure_' + s.unique_id
            WITH s, dept_struct, r1,
                 CASE WHEN dept_struct IS NOT NULL 
                      THEN [(dept_struct)-[r]-(d:{dept}) | d] 
                      ELSE [] 
                 END as departments
            
            // Check for curriculum structure and key stages
            OPTIONAL MATCH (s)-[r2]-(curr_struct:{curr_struct})
            WHERE curr_struct.unique_id = 'CurriculumStructure_' + s.unique_id
            WITH s, dept_struct, r1, departments, curr_struct, r2,
                 CASE WHEN curr_struct IS NOT NULL 
                      THEN [(curr_struct)-[r]-(k:{key_stage}) | k] 
                      ELSE [] 
                 END as key_stages
            
            // Check for pastoral structure and year groups
            OPTIONAL MATCH (s)-[r3]-(past_struct:{past_struct})
            WHERE past_struct.unique_id = 'PastoralStructure_' + s.unique_id
            WITH dept_struct, r1, departments, curr_struct, r2, key_stages, past_struct, r3,
                 CASE WHEN past_struct IS NOT NULL 
                      THEN [(past_struct)-[r]-(y:{year_group}) | y] 
                      ELSE [] 
                 END as year_groups
            
            // Return structure information
            RETURN {{
                has_detailed: 
                    dept_struct IS NOT NULL AND r1 IS NOT NULL AND size(departments) > 0 AND
                    curr_struct IS NOT NULL AND r2 IS NOT NULL AND size(key_stages) > 0 AND
                    past_struct IS NOT NULL AND r3 IS NOT NULL AND size(year_groups) > 0,
                department_structure: {{
                    exists: dept_struct IS NOT NULL AND r1 IS NOT NULL,
                    has_departments: size(departments) > 0,
                    department_count: size(departments),
                    node_id: dept_struct.unique_id
                }},
                curriculum_structure: {{
                    exists: curr_struct IS NOT NULL AND r2 IS NOT NULL,
                    has_key_stages: size(key_stages) > 0,
                    key_stage_count: size(key_stages),
                    node_id: curr_struct.unique_id
                }},
                pastoral_structure: {{
                    exists: past_struct IS NOT NULL AND r3 IS NOT NULL,
                    has_year_groups: size(year_groups) > 0,
                    year_group_count: size(year_groups),
                    node_id: past_struct.unique_id
                }}
            }} as status
        """.format(
            school=NodeLabels.SCHOOL.value,
            dept_struct=NodeLabels.DEPARTMENT_STRUCTURE.value,
            curr_struct=NodeLabels.CURRICULUM_STRUCTURE.value,
            past_struct=NodeLabels.PASTORAL_STRUCTURE.value,
            dept=NodeLabels.DEPARTMENT.value,
            key_stage=NodeLabels.KEY_STAGE.value,
            year_group=NodeLabels.YEAR_GROUP.value
        )

    @staticmethod
    def get_schema_definition() -> SchemaDefinition:
        """Get the schema definition instance"""
        return SchemaDefinition()

    @staticmethod
    def get_schema_creation_queries() -> List[str]:
        """Get queries to create the schema"""
        return SchemaDefinition.get_schema_creation_queries()

    @staticmethod
    def get_schema_verification_queries() -> Dict[str, str]:
        """Get queries to verify schema state"""
        return SchemaDefinition.get_schema_verification_queries()

    @staticmethod
    def get_schema_info() -> Dict[str, List[Dict]]:
        """Get human-readable schema information"""
        return SchemaDefinition.get_schema_info()

class GraphProvider:
    def __init__(self):
        """Initialize the graph provider with Neo4j connection."""
        self.neontology = NeontologyProvider()
        self.graph_naming = GraphNamingProvider()
        self.logger = logging.getLogger(__name__)

    def check_schema_status(self, database_name: str) -> Dict[str, Any]:
        """
        Checks the current state of the schema in the specified database.
        Returns a dictionary containing information about constraints, indexes, and labels.
        """
        try:
            verification_queries = SchemaDefinition.get_schema_verification_queries()
            expected_schema = SchemaDefinition.get_schema_info()
            
            # Get current schema state
            constraints = self.neontology.run_query(verification_queries["constraints"], {}, database_name)
            indexes = self.neontology.run_query(verification_queries["indexes"], {}, database_name)
            labels = self.neontology.run_query(verification_queries["labels"], {}, database_name)
            
            # Process results
            current_constraints = [c["name"] for c in constraints]
            current_indexes = [i["name"] for i in indexes]
            current_labels = [l["label"] for l in labels]
            
            # Expected values
            expected_labels = [node["label"] for node in expected_schema["nodes"]]
            
            return {
                "constraints": current_constraints,
                "constraints_valid": len(current_constraints) >= 4,  # We expect at least 4 unique constraints
                "indexes": current_indexes,
                "indexes_valid": len(current_indexes) >= 5,  # We expect at least 5 indexes
                "labels": current_labels,
                "labels_valid": all(label in current_labels for label in expected_labels)
            }
        except Exception as e:
            self.logger.error(f"Error checking schema status: {str(e)}")
            return {
                "constraints": [], "constraints_valid": False,
                "indexes": [], "indexes_valid": False,
                "labels": [], "labels_valid": False
            }

    def initialize_schema(self, database_name: str) -> None:
        """
        Initializes the schema for the specified database by creating all necessary
        constraints and indexes.
        """
        try:
            creation_queries = SchemaDefinition.get_schema_creation_queries()
            
            for query in creation_queries:
                self.neontology.cypher_write(query, {}, database_name)
                
            self.logger.info(f"Schema initialized successfully for database {database_name}")
        except Exception as e:
            self.logger.error(f"Error initializing schema: {str(e)}")
            raise

    def get_schema_info(self) -> Dict[str, Any]:
        """
        Returns the schema definition information.
        """
        return SchemaDefinition.get_schema_info()
