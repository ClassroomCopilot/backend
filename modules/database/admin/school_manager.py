import os
from modules.logger_tool import initialise_logger
from supabase import create_client
import json
import pandas as pd

import modules.database.init.xl_tools as xl
from modules.database.tools.filesystem_tools import ClassroomCopilotFilesystem
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
from modules.database.admin.neontology_provider import NeontologyProvider
from modules.database.admin.graph_provider import GraphNamingProvider, NodeLabels, RelationshipTypes, PropertyKeys
from modules.database.schemas import entity_neo, curriculum_neo
from modules.database.schemas.relationships import curricular_relationships, entity_relationships, entity_curriculum_rels

class SchoolManager:
    def __init__(self):
        self.driver = driver_tools.get_driver()
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        self.neontology = NeontologyProvider()
        self.graph_naming = GraphNamingProvider()
        
        # Initialize Supabase client with correct URL and service role key
        supabase_url = os.getenv("SUPABASE_BACKEND_URL")
        service_role_key = os.getenv("SERVICE_ROLE_KEY")
        
        self.logger.info(f"Initializing Supabase client with URL: {supabase_url}")
        self.supabase = create_client(supabase_url, service_role_key)
        
        # Set headers for admin operations
        self.supabase.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        
        # Set storage client headers explicitly
        self.supabase.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })

    def create_schools_database(self):
        """Creates the main cc.ccschools database in Neo4j"""
        try:
            db_name = "cc.ccschools"
            with self.driver.session() as session:
                return self._extracted_from_create_private_database(
                    session, db_name, f'Created database {db_name}'
                )
        except Exception as e:
            self.logger.error(f"Error creating schools database: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    def create_school_node(self, school_data):
        """Creates a school node in cc.ccschools database and stores TLDraw file in Supabase"""
        try:
            # Convert Supabase school data to SchoolNode using GraphNamingProvider
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
                "x-upsert": "true",  # Update if exists
                "metadata": {
                    "establishment_urn": school_data['urn'],
                    "establishment_name": school_data['establishment_name']
                }
            }
            
            try:
                # Create a fresh service role client for storage operations
                self.logger.info("Creating fresh service role client for storage operations")
                service_client = create_client(
                    os.getenv("SUPABASE_BACKEND_URL"),
                    os.getenv("SERVICE_ROLE_KEY")
                )
                
                self.logger.debug(f"Service client created with URL: {os.getenv('SUPABASE_BACKEND_URL')}")
                
                service_client.headers = {
                    "apiKey": os.getenv("SERVICE_ROLE_KEY"),
                    "Authorization": f"Bearer {os.getenv('SERVICE_ROLE_KEY')}",
                    "Content-Type": "application/json"
                }
                service_client.storage._client.headers.update({
                    "apiKey": os.getenv("SERVICE_ROLE_KEY"),
                    "Authorization": f"Bearer {os.getenv('SERVICE_ROLE_KEY')}",
                    "Content-Type": "application/json"
                })
                
                self.logger.debug("Headers set for service client and storage client")
                
                # Upload to Supabase storage using service role client
                self.logger.info(f"Uploading tldraw file for school {school_data['urn']}")
                self.logger.debug(f"File path: {file_path}")
                self.logger.debug(f"File options: {file_options}")
                
                # First, ensure the bucket exists
                self.logger.info("Checking if bucket cc.ccschools exists")
                try:
                    bucket = service_client.storage.get_bucket("cc.ccschools")
                    self.logger.info("Bucket cc.ccschools exists")
                except Exception as bucket_error:
                    self.logger.error(f"Error checking bucket: {str(bucket_error)}")
                    if hasattr(bucket_error, 'response'):
                        self.logger.error(f"Bucket error response: {bucket_error.response.text if hasattr(bucket_error.response, 'text') else bucket_error.response}")
                    raise bucket_error
                
                # Attempt the upload
                self.logger.info("Attempting file upload")
                result = service_client.storage.from_("cc.ccschools").upload(
                    path=file_path,
                    file=json.dumps(tldraw_data).encode(),
                    file_options=file_options
                )
                self.logger.info(f"Upload successful. Result: {result}")
                
            except Exception as upload_error:
                self.logger.error(f"Error uploading tldraw file: {str(upload_error)}")
                if hasattr(upload_error, 'response'):
                    self.logger.error(f"Upload error response: {upload_error.response.text if hasattr(upload_error.response, 'text') else upload_error.response}")
                raise upload_error
            
            # Create node in Neo4j using Neontology
            with self.neontology as neo:
                self.logger.info(f"Creating school node in Neo4j: {school_node.to_dict()}")
                neo.create_or_merge_node(school_node, database="cc.ccschools", operation="merge")
                return {"status": "success", "node": school_node}
                
        except Exception as e:
            self.logger.error(f"Error creating school node: {str(e)}")
            return {"status": "error", "message": str(e)}

    def create_private_database(self, school_data):
        """Creates a private database for a specific school"""
        try:
            private_db_name = f"cc.ccschools.{school_data['urn']}"
            with self.driver.session() as session:
                return self._extracted_from_create_private_database(
                    session, private_db_name, 'Created private database '
                )
        except Exception as e:
            self.logger.error(f"Error creating private database: {str(e)}")
            return {"status": "error", "message": str(e)}

    # TODO Rename this here and in `create_schools_database` and `create_private_database`
    def _extracted_from_create_private_database(self, session, arg1, arg2):
        session_tools.create_database(session, arg1)
        self.logger.info(f"{arg2}{arg1}")
        return {
            "status": "success",
            "message": f"Database {arg1} created successfully",
        }

    def create_basic_structure(self, school_node, database_name):
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

    def create_detailed_structure(self, school_node, database_name, excel_file):
        """Creates detailed structural nodes from Excel file"""
        try:
            # First, store the Excel file in Supabase
            file_path = f"{school_node.urn}/structure.xlsx"
            file_options = {
                "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "x-upsert": "true"
            }
            
            # Upload Excel file to storage
            self.supabase.storage.from_("cc.ccschools").upload(
                path=file_path,
                file=excel_file,
                file_options=file_options
            )
            
            # Process Excel file
            dataframes = xl.create_dataframes(excel_file)
            
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
    
    def sort_year_groups(self, df):
        df = df.copy()
        df['YearGroupNumeric'] = pd.to_numeric(df['YearGroup'], errors='coerce')
        return df.sort_values(by='YearGroupNumeric')
