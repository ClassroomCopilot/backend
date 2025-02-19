import os
from modules.logger_tool import initialise_logger
import modules.database.tools.neo4j_driver_tools as driver_tools
import modules.database.tools.neo4j_session_tools as session_tools
from modules.database.schemas.entity_neo import SchoolNode
import json
from supabase import create_client

class SchoolManager:
    def __init__(self):
        self.driver = driver_tools.get_driver()
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        
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
                session_tools.create_database(session, db_name)
                self.logger.info(f"Created database {db_name}")
                return {"status": "success", "message": f"Database {db_name} created successfully"}
        except Exception as e:
            self.logger.error(f"Error creating schools database: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    def create_school_node(self, school_data):
        """Creates a school node in cc.ccschools database and stores TLDraw file in Supabase"""
        try:
            # Convert Supabase school data to SchoolNode
            school_node = SchoolNode(
                unique_id=f"School_{school_data['urn']}",
                path=f"/schools/cc.ccschools/{school_data['urn']}",
                urn=school_data['urn'],
                establishment_number=school_data['establishment_number'],
                establishment_name=school_data['establishment_name'],
                establishment_type=school_data['establishment_type'],
                establishment_status=school_data['establishment_status'],
                phase_of_education=school_data['phase_of_education'],
                statutory_low_age=int(school_data['statutory_low_age']) if school_data.get('statutory_low_age') is not None else 0,
                statutory_high_age=int(school_data['statutory_high_age']) if school_data.get('statutory_high_age') is not None else 0,
                religious_character=school_data.get('religious_character'),
                school_capacity=int(school_data['school_capacity']) if school_data.get('school_capacity') is not None else 0,
                school_website=school_data.get('school_website', ''),
                ofsted_rating=school_data.get('ofsted_rating')
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
                        "id": f"School_{school_data['urn']}",
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
                self.logger.info("Checking if bucket cc.ccschools.public exists")
                try:
                    bucket = service_client.storage.get_bucket("cc.ccschools.public")
                    self.logger.info("Bucket cc.ccschools.public exists")
                except Exception as bucket_error:
                    self.logger.error(f"Error checking bucket: {str(bucket_error)}")
                    if hasattr(bucket_error, 'response'):
                        self.logger.error(f"Bucket error response: {bucket_error.response.text if hasattr(bucket_error.response, 'text') else bucket_error.response}")
                    raise bucket_error
                
                # Attempt the upload
                self.logger.info("Attempting file upload")
                result = service_client.storage.from_("cc.ccschools.public").upload(
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
            
            # Create node in Neo4j
            with self.driver.session(database="cc.ccschools") as session:
                result = session.write_transaction(self._create_school_node_tx, school_node)
                return {"status": "success", "node": result}
        except Exception as e:
            self.logger.error(f"Error creating school node: {str(e)}")
            return {"status": "error", "message": str(e)}
            
    @staticmethod
    def _create_school_node_tx(tx, school_node: SchoolNode):
        """Transaction function for creating school node"""
        # Use the SchoolNode model's to_dict method to get all properties
        node_data = school_node.to_dict()
        # Remove any metadata fields that shouldn't be in the node
        node_data.pop('__primarylabel__', None)
        node_data.pop('created', None)
        node_data.pop('merged', None)
        
        # Build the query dynamically from the node data
        properties = ', '.join(f"{key}: ${key}" for key in node_data.keys())
        query = f"CREATE (s:School {{{properties}}}) RETURN s"
        
        result = tx.run(query, node_data)
        return result.single()

