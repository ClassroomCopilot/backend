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
        self.supabase = create_client(
            os.getenv("VITE_SUPABASE_URL", "http://kong:8000"),
            os.getenv("SERVICE_ROLE_KEY")
        )
        
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
                statutory_low_age=float(school_data['statutory_low_age']) if school_data.get('statutory_low_age') is not None else 0.0,
                statutory_high_age=float(school_data['statutory_high_age']) if school_data.get('statutory_high_age') is not None else 0.0,
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
            
            # Upload to Supabase storage
            self.supabase.storage.from_("cc.ccschools.public").upload(
                file_path,
                json.dumps(tldraw_data).encode(),
                file_options
            )
            
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

