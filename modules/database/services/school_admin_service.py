import os
from typing import Dict, List, Optional, BinaryIO
import json
import pandas as pd
from modules.logger_tool import initialise_logger
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
from modules.database.admin.neontology_provider import NeontologyProvider
from modules.database.admin.graph_provider import GraphNamingProvider
from modules.database.schemas import entity_neo, curriculum_neo
from modules.database.schemas.relationships import curricular_relationships, entity_relationships, entity_curriculum_rels
from modules.database.supabase.utils.storage import StorageManager

class SchoolAdminService:
    def __init__(self):
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        self.driver = driver_tools.get_driver()
        self.neontology = NeontologyProvider()
        self.graph_naming = GraphNamingProvider()
        self.storage = StorageManager()

    def create_schools_database(self) -> Dict:
        """Creates the main cc.ccschools database in Neo4j"""
        try:
            db_name = "cc.ccschools"
            
            # Use driver directly to create database
            with self.driver.session() as session:
                # First check if database exists
                result = session.run("SHOW DATABASES")
                databases = [record["name"] for record in result]
                
                if db_name not in databases:
                    session.run(f"CREATE DATABASE {db_name}")
                    self.logger.info(f"Created database {db_name}")
                    return {
                        "status": "success",
                        "message": f"Database {db_name} created successfully"
                    }
                else:
                    self.logger.info(f"Database {db_name} already exists")
                    return {
                        "status": "success",
                        "message": f"Database {db_name} already exists"
                    }
                
        except Exception as e:
            self.logger.error(f"Error creating schools database: {str(e)}")
            return {"status": "error", "message": str(e)}

    def create_school_node(self, school_data: Dict) -> Dict:
        """Creates a school node in cc.ccschools database and stores TLDraw file in Supabase"""
        try:
            # Convert school data to SchoolNode
            school_unique_id = self.graph_naming.get_school_unique_id(school_data['urn'])
            school_path = self.graph_naming.get_school_path("cc.ccschools", school_data['urn'])
            
            school_node = entity_neo.SchoolNode(
                unique_id=school_unique_id,
                path=school_path,
                urn=school_data['urn'],
                establishment_number=school_data['establishment_number'],
                establishment_name=school_data['establishment_name'],
                establishment_type=school_data['establishment_type'],
                establishment_status=school_data['establishment_status'],
                phase_of_education=school_data['phase_of_education'] if school_data['phase_of_education'] not in [None, ''] else None,
                statutory_low_age=int(school_data['statutory_low_age']) if school_data.get('statutory_low_age') is not None else 0,
                statutory_high_age=int(school_data['statutory_high_age']) if school_data.get('statutory_high_age') is not None else 0,
                religious_character=school_data.get('religious_character') if school_data.get('religious_character') not in [None, ''] else None,
                school_capacity=int(school_data['school_capacity']) if school_data.get('school_capacity') is not None else 0,
                school_website=school_data.get('school_website', ''),
                ofsted_rating=school_data.get('ofsted_rating') if school_data.get('ofsted_rating') not in [None, ''] else None
            )
            
            # Create default tldraw file data
            tldraw_data = {
                "document": {
                    "version": 1,
                    "id": school_data['urn'],
                    "name": school_data['establishment_name'],
                    "meta": {
                        "created_at": "",
                        "updated_at": "",
                        "creator_id": "",
                        "is_template": False,
                        "is_snapshot": False,
                        "is_draft": False,
                        "template_id": None,
                        "snapshot_id": None,
                        "draft_id": None
                    }
                },
                "schema": {
                    "schemaVersion": 1,
                    "storeVersion": 4,
                    "recordVersions": {
                        "asset": {
                            "version": 1,
                            "subTypeKey": "type",
                            "subTypeVersions": {}
                        },
                        "camera": {
                            "version": 1
                        },
                        "document": {
                            "version": 2
                        },
                        "instance": {
                            "version": 22
                        },
                        "instance_page_state": {
                            "version": 5
                        },
                        "page": {
                            "version": 1
                        },
                        "shape": {
                            "version": 3,
                            "subTypeKey": "type",
                            "subTypeVersions": {
                                "cc-school-node": 1
                            }
                        },
                        "instance_presence": {
                            "version": 5
                        },
                        "pointer": {
                            "version": 1
                        }
                    }
                },
                "store": {
                    "document:document": {
                        "gridSize": 10,
                        "name": school_data['establishment_name'],
                        "meta": {},
                        "id": school_data['urn'],
                        "typeName": "document"
                    },
                    "page:page": {
                        "meta": {},
                        "id": "page",
                        "name": "Page 1",
                        "index": "a1",
                        "typeName": "page"
                    },
                    "shape:school-node": {
                        "x": 0,
                        "y": 0,
                        "rotation": 0,
                        "type": "cc-school-node",
                        "id": school_unique_id,
                        "parentId": "page",
                        "index": "a1",
                        "props": school_node.to_dict(),
                        "typeName": "shape"
                    },
                    "instance:instance": {
                        "id": "instance",
                        "currentPageId": "page",
                        "typeName": "instance"
                    },
                    "camera:camera": {
                        "x": 0,
                        "y": 0,
                        "z": 1,
                        "id": "camera",
                        "typeName": "camera"
                    }
                }
            }
            
            # Store tldraw file in Supabase storage
            file_path = f"{school_data['urn']}/tldraw.json"
            file_options = {
                "content-type": "application/json",
                "x-upsert": "true",
                "metadata": {
                    "establishment_urn": school_data['urn'],
                    "establishment_name": school_data['establishment_name']
                }
            }
            
            # Upload file
            self.storage.upload_file(
                bucket_id="cc.ccschools",
                file_path=file_path,
                file_data=json.dumps(tldraw_data).encode(),
                content_type="application/json",
                upsert=True
            )
            
            # Create node in Neo4j
            with self.neontology as neo:
                self.logger.info(f"Creating school node in Neo4j: {school_node.to_dict()}")
                neo.create_or_merge_node(school_node, database="cc.ccschools", operation="merge")
                return {"status": "success", "node": school_node}
                
        except Exception as e:
            self.logger.error(f"Error creating school node: {str(e)}")
            return {"status": "error", "message": str(e)}

    def create_private_database(self, school_data: Dict) -> Dict:
        """Creates a private database for a specific school"""
        try:
            private_db_name = f"cc.ccschools.{school_data['urn']}"
            with self.driver.session() as session:
                session_tools.create_database(session, private_db_name)
                self.logger.info(f"Created private database {private_db_name}")
                return {
                    "status": "success",
                    "message": f"Database {private_db_name} created successfully"
                }
        except Exception as e:
            self.logger.error(f"Error creating private database: {str(e)}")
            return {"status": "error", "message": str(e)}

    def create_basic_structure(self, school_node: entity_neo.SchoolNode, database_name: str) -> Dict:
        """Creates basic structural nodes in the specified database"""
        try:
            # Create filesystem paths
            fs_handler = ClassroomCopilotFilesystem(database_name, init_run_type="school")
            
            # Create Department Structure node
            department_structure_node_unique_id = f"DepartmentStructure_{school_node.unique_id}"
            _, department_path = fs_handler.create_school_department_directory(school_node.path, "departments")
            department_structure_node = entity_neo.DepartmentStructureNode(
                unique_id=department_structure_node_unique_id,
                path=department_path
            )
            
            # Create Curriculum Structure node
            _, curriculum_path = fs_handler.create_school_curriculum_directory(school_node.path)
            curriculum_node = curriculum_neo.CurriculumStructureNode(
                unique_id=f"CurriculumStructure_{school_node.unique_id}",
                path=curriculum_path
            )
            
            # Create Pastoral Structure node
            _, pastoral_path = fs_handler.create_school_pastoral_directory(school_node.path)
            pastoral_node = curriculum_neo.PastoralStructureNode(
                unique_id=f"PastoralStructure_{school_node.unique_id}",
                path=pastoral_path
            )
            
            with self.neontology as neo:
                # Create nodes
                neo.create_or_merge_node(department_structure_node, database=str(database_name), operation='merge')
                fs_handler.create_default_tldraw_file(department_structure_node.path, department_structure_node.to_dict())
                
                neo.create_or_merge_node(curriculum_node, database=str(database_name), operation='merge')
                fs_handler.create_default_tldraw_file(curriculum_node.path, curriculum_node.to_dict())
                
                neo.create_or_merge_node(pastoral_node, database=database_name, operation='merge')
                fs_handler.create_default_tldraw_file(pastoral_node.path, pastoral_node.to_dict())
                
                # Create relationships
                neo.create_or_merge_relationship(
                    entity_relationships.SchoolHasDepartmentStructure(source=school_node, target=department_structure_node),
                    database=database_name, operation='merge'
                )
                
                neo.create_or_merge_relationship(
                    entity_curriculum_rels.SchoolHasCurriculumStructure(source=school_node, target=curriculum_node),
                    database=database_name, operation='merge'
                )
                
                neo.create_or_merge_relationship(
                    entity_curriculum_rels.SchoolHasPastoralStructure(source=school_node, target=pastoral_node),
                    database=database_name, operation='merge'
                )
            
            return {
                "status": "success",
                "message": "Basic structure created successfully",
                "nodes": {
                    "department_structure": department_structure_node,
                    "curriculum_structure": curriculum_node,
                    "pastoral_structure": pastoral_node
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating basic structure: {str(e)}")
            return {"status": "error", "message": str(e)}

    def create_detailed_structure(self, school_node: entity_neo.SchoolNode, database_name: str, excel_file: BinaryIO) -> Dict:
        """Creates detailed structural nodes from Excel file"""
        try:
            # Store Excel file in Supabase
            file_path = f"{school_node.urn}/structure.xlsx"
            
            # Upload Excel file
            self.storage.upload_file(
                bucket_id="cc.ccschools",
                file_path=file_path,
                file_data=excel_file.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                upsert=True
            )
            
            # Process Excel file
            dataframes = pd.read_excel(excel_file, sheet_name=None)
            
            # Get existing basic structure nodes
            with self.neontology as neo:
                result = neo.cypher_read("""
                    MATCH (s:School {unique_id: $school_id})
                    OPTIONAL MATCH (s)-[:HAS_DEPARTMENT_STRUCTURE]->(ds:DepartmentStructure)
                    OPTIONAL MATCH (s)-[:HAS_CURRICULUM_STRUCTURE]->(cs:CurriculumStructure)
                    OPTIONAL MATCH (s)-[:HAS_PASTORAL_STRUCTURE]->(ps:PastoralStructure)
                    RETURN ds, cs, ps
                """, {"school_id": school_node.unique_id}, database=database_name)
                
                if not result:
                    raise Exception("Basic structure not found")
                
                department_structure = result['ds']
                curriculum_structure = result['cs']
                pastoral_structure = result['ps']
            
            # Create departments and subjects
            unique_departments = dataframes['keystagesyllabuses']['Department'].dropna().unique()
            
            fs_handler = ClassroomCopilotFilesystem(database_name, init_run_type="school")
            node_library = {}
            
            with self.neontology as neo:
                for department_name in unique_departments:
                    _, department_path = fs_handler.create_school_department_directory(school_node.path, department_name)
                    
                    department_node = entity_neo.DepartmentNode(
                        unique_id=f"Department_{school_node.unique_id}_{department_name.replace(' ', '_')}",
                        department_name=department_name,
                        path=department_path
                    )
                    neo.create_or_merge_node(department_node, database=database_name, operation='merge')
                    fs_handler.create_default_tldraw_file(department_node.path, department_node.to_dict())
                    node_library[f'department_{department_name}'] = department_node
                    
                    # Link to department structure
                    neo.create_or_merge_relationship(
                        entity_relationships.DepartmentStructureHasDepartment(
                            source=department_structure,
                            target=department_node
                        ),
                        database=database_name,
                        operation='merge'
                    )
                
                # Create year groups
                year_groups = self.sort_year_groups(dataframes['yeargroupsyllabuses'])['YearGroup'].unique()
                last_year_group_node = None
                
                for year_group in year_groups:
                    numeric_year_group = pd.to_numeric(year_group, errors='coerce')
                    if pd.notna(numeric_year_group):
                        _, year_group_path = fs_handler.create_pastoral_year_group_directory(
                            pastoral_structure.path,
                            str(int(numeric_year_group))
                        )
                        
                        year_group_node = curriculum_neo.YearGroupNode(
                            unique_id=f"YearGroup_{school_node.unique_id}_YGrp{int(numeric_year_group)}",
                            year_group=str(int(numeric_year_group)),
                            year_group_name=f"Year {int(numeric_year_group)}",
                            path=year_group_path
                        )
                        neo.create_or_merge_node(year_group_node, database=database_name, operation='merge')
                        fs_handler.create_default_tldraw_file(year_group_node.path, year_group_node.to_dict())
                        node_library[f'year_group_{int(numeric_year_group)}'] = year_group_node
                        
                        # Create sequential relationship
                        if last_year_group_node:
                            neo.create_or_merge_relationship(
                                curricular_relationships.YearGroupFollowsYearGroup(
                                    source=last_year_group_node,
                                    target=year_group_node
                                ),
                                database=database_name,
                                operation='merge'
                            )
                        last_year_group_node = year_group_node
                        
                        # Link to pastoral structure
                        neo.create_or_merge_relationship(
                            curricular_relationships.PastoralStructureIncludesYearGroup(
                                source=pastoral_structure,
                                target=year_group_node
                            ),
                            database=database_name,
                            operation='merge'
                        )
                
                # Create key stages
                key_stages = dataframes['keystagesyllabuses']['KeyStage'].unique()
                last_key_stage_node = None
                
                for key_stage in sorted(key_stages):
                    _, key_stage_path = fs_handler.create_curriculum_key_stage_directory(
                        curriculum_structure.path,
                        str(key_stage)
                    )
                    
                    key_stage_node = curriculum_neo.KeyStageNode(
                        unique_id=f"KeyStage_{curriculum_structure.unique_id}_KStg{key_stage}",
                        key_stage_name=f"Key Stage {key_stage}",
                        key_stage=str(key_stage),
                        path=key_stage_path
                    )
                    neo.create_or_merge_node(key_stage_node, database=database_name, operation='merge')
                    fs_handler.create_default_tldraw_file(key_stage_node.path, key_stage_node.to_dict())
                    node_library[f'key_stage_{key_stage}'] = key_stage_node
                    
                    # Create sequential relationship
                    if last_key_stage_node:
                        neo.create_or_merge_relationship(
                            curricular_relationships.KeyStageFollowsKeyStage(
                                source=last_key_stage_node,
                                target=key_stage_node
                            ),
                            database=database_name,
                            operation='merge'
                        )
                    last_key_stage_node = key_stage_node
                    
                    # Link to curriculum structure
                    neo.create_or_merge_relationship(
                        curricular_relationships.CurriculumStructureIncludesKeyStage(
                            source=curriculum_structure,
                            target=key_stage_node
                        ),
                        database=database_name,
                        operation='merge'
                    )
            
            return {
                "status": "success",
                "message": "Detailed structure created successfully",
                "node_library": node_library
            }
            
        except Exception as e:
            self.logger.error(f"Error creating detailed structure: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def sort_year_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        """Helper function to sort year groups numerically"""
        df = df.copy()
        df['YearGroupNumeric'] = pd.to_numeric(df['YearGroup'], errors='coerce')
        return df.sort_values(by='YearGroupNumeric')

    def check_schools_database(self) -> Dict:
        """Check if the schools database exists and is properly initialized"""
        try:
            db_name = "cc.ccschools"
            
            # Use driver directly to check database existence
            with self.driver.session() as session:
                result = session.run("SHOW DATABASES")
                databases = [record["name"] for record in result]
                
                if db_name in databases:
                    return {
                        "status": "success",
                        "message": f"Database {db_name} exists and is accessible"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Database {db_name} does not exist"
                    }
                
        except Exception as e:
            self.logger.error(f"Error checking schools database: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
