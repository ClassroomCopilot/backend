#!/usr/bin/env python3
"""
ClassroomCopilot Initialization System
This script orchestrates the initialization of all system components.
"""
import os
import sys
import json
import time
import logging
import requests
import csv
from typing import Dict
from modules.database.services.school_admin_service import SchoolAdminService
from modules.database.services.graph_service import GraphService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cc-init")

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://kong:8000")
SERVICE_ROLE_KEY = os.environ.get("SERVICE_ROLE_KEY")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ADMIN_NAME = os.environ.get("ADMIN_NAME", "Super Admin")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:5000")

class InitializationSystem:
    """Main initialization system that orchestrates all components"""
    
    def __init__(self, manager=None):
        if manager:
            self.manager = manager
            self.supabase_headers = manager.supabase_headers
            self.status = manager.status
        else:
            # Fallback to original standalone behavior
            self.supabase_headers = {
                "apikey": os.getenv("SERVICE_ROLE_KEY"),
                "Authorization": f"Bearer {os.getenv('SERVICE_ROLE_KEY')}",
                "Content-Type": "application/json"
            }
            self.manager = None
            self.status = self._load_status()
            
        self.admin_token = None
        self.init_dir = "/init"
        self.data_dir = os.path.join(self.init_dir, "data")
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Copy template files if they don't exist
        self._ensure_data_files()
    
    def _ensure_data_files(self):
        """Ensure required data files exist"""
        # Check for schools data file
        csv_path = os.path.join(self.data_dir, "sample_schools.csv")
        if not os.path.exists(csv_path):
            logger.warning(f"Schools data file not found at {csv_path}")
    
    def _load_status(self) -> Dict:
        """Load initialization status from file or create default"""
        try:
            with open("/init/status.json", "r") as f:
                status = json.load(f)
                
            # Verify all required keys exist
            default_status = {
                "super_admin_created": False,
                "admin_token_obtained": False,
                "storage": {
                    "initialized": False,
                    "buckets": {
                        "cc.ccusers": False,
                        "cc.ccschools": False
                    }
                },
                "neo4j": {
                    "initialized": False,
                    "database_created": False,
                    "schema_initialized": False,
                    "schools_imported": False
                },
                "completed": False,
                "timestamp": None,
                "steps": []
            }
            
            # Recursively update status with any missing keys
            def update_dict(current: Dict, default: Dict) -> Dict:
                for key, value in default.items():
                    if key not in current:
                        current[key] = value
                    elif isinstance(value, dict) and isinstance(current[key], dict):
                        current[key] = update_dict(current[key], value)
                return current
            
            status = update_dict(status, default_status)
            self._save_status(status)
            return status
            
        except (FileNotFoundError, json.JSONDecodeError):
            default_status = {
                "super_admin_created": False,
                "admin_token_obtained": False,
                "storage": {
                    "initialized": False,
                    "buckets": {
                        "cc.ccusers": False,
                        "cc.ccschools": False
                    }
                },
                "neo4j": {
                    "initialized": False,
                    "database_created": False,
                    "schema_initialized": False,
                    "schools_imported": False
                },
                "completed": False,
                "timestamp": None,
                "steps": []
            }
            self._save_status(default_status)
            return default_status
    
    def _save_status(self, status: Dict) -> None:
        """Save initialization status to file"""
        if self.manager:
            self.manager._save_status(status)
        else:
            # Fallback to direct file save
            os.makedirs(os.path.dirname("/init/status.json"), exist_ok=True)
            with open("/init/status.json", "w") as f:
                json.dump(status, f, indent=2)
    
    def update_status(self, key: str, value: any) -> None:
        """Update a specific status key and save"""
        if isinstance(value, dict):
            if key not in self.status:
                self.status[key] = {}
            self.status[key].update(value)
        else:
            self.status[key] = value
        
        self.status["timestamp"] = time.time()
        self._save_status(self.status)
    
    def wait_for_services(self) -> bool:
        """Wait for required services to be available"""
        logger.info("Waiting for services to be available...")
        
        # Wait for Supabase
        max_retries = 30
        retry_count = 0
        while retry_count < max_retries:
            try:
                response = requests.get(f"{SUPABASE_URL}/rest/v1/?apikey={SERVICE_ROLE_KEY}")
                if response.status_code < 500:
                    logger.info("Supabase is available")
                    break
            except requests.RequestException:
                pass
            
            retry_count += 1
            logger.info(f"Waiting for Supabase... ({retry_count}/{max_retries})")
            time.sleep(5)
        
        if retry_count >= max_retries:
            logger.error("Supabase is not available after maximum retries")
            return False
        
        return True
    
    def check_super_admin_exists(self) -> bool:
        """Check if super admin exists in both auth and profiles"""
        try:
            # 1. Check auth.users table
            response = requests.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=self.supabase_headers
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to check auth users: {response.text}")
                return False
            
            try:
                # Parse the response
                auth_data = response.json()
                
                # Check if we have the expected structure
                if not isinstance(auth_data, dict) or 'users' not in auth_data:
                    logger.error(f"Unexpected auth users response structure: {auth_data}")
                    return False
                
                # Find our admin in the list of users
                auth_user = next(
                    (user for user in auth_data['users'] 
                     if isinstance(user, dict) and user.get("email") == ADMIN_EMAIL),
                    None
                )
                
                if not auth_user:
                    logger.info("Super admin not found in auth.users")
                    return False
                
                user_id = auth_user.get("id")
                logger.info(f"Found auth user with ID: {user_id}")
                
                # Verify the user has the correct metadata
                app_metadata = auth_user.get("app_metadata", {})
                if app_metadata.get("role") != "supabase_admin":
                    logger.info("User exists but is not a supabase_admin")
                    return False
                
                # 2. Check public.profiles table
                response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/profiles",
                    headers=self.supabase_headers,
                    params={
                        "select": "*",
                        "email": f"eq.{ADMIN_EMAIL}"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to check profiles: {response.text}")
                    return False
                
                try:
                    profiles = response.json()
                    if not isinstance(profiles, list):
                        logger.error(f"Unexpected profiles response format: {profiles}")
                        return False
                    
                    if not profiles:
                        logger.info("Super admin not found in public.profiles")
                        return False
                    
                    profile = profiles[0]
                    if not isinstance(profile, dict):
                        logger.error(f"Unexpected profile format: {profile}")
                        return False
                    
                    # 3. Verify admin status
                    user_type = profile.get("user_type")
                    if user_type != "admin":
                        logger.info(f"User exists but is not an admin (type: {user_type})")
                        return False
                    
                    logger.info("Super admin exists and is properly configured")
                    return True
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse profiles response: {str(e)}")
                    return False
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse auth users response: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Error checking super admin existence: {str(e)}")
            return False
    
    def create_super_admin(self) -> bool:
        """Create the super admin user"""
        if self.status.get("super_admin_created"):
            if self.check_super_admin_exists():
                logger.info("Super admin already exists and is properly configured")
                return True
            else:
                logger.warning("Status indicates super admin created but verification failed")
        
        logger.info(f"Creating super admin user with email: {os.getenv('ADMIN_EMAIL')}")
        
        try:
            # Create user data structure directly
            user_data = {
                "email": os.getenv('ADMIN_EMAIL'),
                "password": os.getenv('ADMIN_PASSWORD'),
                "email_confirm": True,
                "user_metadata": {
                    "name": os.getenv('ADMIN_NAME')
                },
                "app_metadata": {
                    "provider": "email",
                    "providers": ["email"],
                    "role": "supabase_admin"
                }
            }
            
            # Create user via Auth API
            response = requests.post(
                f"{os.getenv('SUPABASE_URL')}/auth/v1/admin/users",
                headers=self.supabase_headers,
                json=user_data
            )
            
            if response.status_code not in (200, 201):
                logger.error(f"Failed to create admin user: {response.text}")
                return False
            
            user_id = response.json().get("id")
            logger.info(f"Created auth user with ID: {user_id}")
            
            # Add a small delay to ensure user is created
            time.sleep(2)
            
            # Call setup_initial_admin function to set admin profile
            response = requests.post(
                f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/setup_initial_admin",
                headers=self.supabase_headers,
                json={
                    "admin_email": os.getenv('ADMIN_EMAIL')
                }
            )
            
            if response.status_code not in (200, 201, 204):
                logger.error(f"Failed to set up admin profile: {response.text}")
                return False
            
            logger.info("Updated user profile to admin type")
            
            # Wait for changes to propagate
            logger.info("Waiting for changes to propagate...")
            time.sleep(2)
            
            # Verify the setup
            if self.check_super_admin_exists():
                logger.info("Super admin exists and is properly configured")
                self.status["super_admin_created"] = True
                self._save_status(self.status)
                logger.info("Super admin created and verified successfully")
                return True
            else:
                logger.error("Failed to verify super admin setup")
                return False
            
        except Exception as e:
            logger.error(f"Error creating super admin: {str(e)}")
            return False
    
    def get_admin_token(self) -> bool:
        """Get an access token for the admin user"""
        if self.status.get("admin_token_obtained"):
            logger.info("Admin token already obtained, skipping...")
            return True
        
        logger.info("Getting admin access token...")
        
        # Add a small delay to ensure auth system is ready
        time.sleep(2)
        
        # Try multiple times with increasing delays
        max_retries = 5
        for retry in range(max_retries):
            try:
                # Sign in with admin credentials
                login_data = {
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                }
                
                logger.info(f"Attempting to login as {ADMIN_EMAIL} (attempt {retry+1}/{max_retries})")
                
                response = requests.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={
                        "apikey": SERVICE_ROLE_KEY,
                        "Content-Type": "application/json"
                    },
                    json=login_data
                )
                
                if response.status_code in (200, 201):
                    # Extract the access token
                    self.admin_token = response.json().get("access_token")
                    
                    if self.admin_token:
                        logger.info("Admin token obtained successfully")
                        self.update_status("admin_token_obtained", True)
                        return True
                    else:
                        logger.error("No access token in response")
                else:
                    logger.error(f"Failed to get admin token (attempt {retry+1}): {response.text}")
                
                # Increase delay with each retry
                wait_time = (retry + 1) * 2
                logger.info(f"Waiting {wait_time} seconds before next attempt...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Error getting admin token: {str(e)}")
                time.sleep((retry + 1) * 2)
        
        # If we get here, all retries failed
        logger.error("Failed to get admin token after multiple attempts")
        
        # As a fallback, try to use the service role key directly
        logger.info("Falling back to using service role key for API calls")
        self.admin_token = SERVICE_ROLE_KEY
        self.update_status("admin_token_obtained", True)
        return True
    
    def log_step(self, step: str, success: bool, message: str = None) -> None:
        """Log a step in the initialization process"""
        step_log = {
            "step": step,
            "success": success,
            "timestamp": time.time(),
            "message": message
        }
        if "steps" not in self.status:
            self.status["steps"] = []
        self.status["steps"].append(step_log)
        self._save_status(self.status)
        
        if success:
            logger.info(f"Step '{step}' completed successfully")
        else:
            logger.error(f"Step '{step}' failed: {message}")
    
    def initialize_storage(self) -> bool:
        """Initialize storage buckets and policies"""
        if self.status["storage"]["initialized"]:
            logger.info("Storage already initialized, skipping...")
            return True
        
        logger.info("Initializing storage buckets and policies...")
        
        try:
            # Define required buckets with their configurations
            required_buckets = [
                {
                    "id": "cc.ccusers",
                    "name": "User Files",
                    "public": False,
                    "file_size_limit": 50 * 1024 * 1024,
                    "allowed_mime_types": [
                        "image/*",
                        "video/*",
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-powerpoint",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "text/plain",
                        "text/csv",
                        "application/json"
                    ]
                },
                {
                    "id": "cc.ccschools",
                    "name": "School Files",
                    "public": False,
                    "file_size_limit": 50 * 1024 * 1024,
                    "allowed_mime_types": [
                        "image/*",
                        "video/*",
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "application/vnd.ms-excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/vnd.ms-powerpoint",
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "text/plain",
                        "text/csv",
                        "application/json"
                    ]
                }
            ]
            
            for bucket_config in required_buckets:
                try:
                    bucket_id = bucket_config["id"]
                    logger.info(f"Creating bucket {bucket_id}")
                    
                    # Check if bucket exists
                    response = requests.get(
                        f"{SUPABASE_URL}/storage/v1/bucket/{bucket_id}",
                        headers=self.supabase_headers
                    )
                    
                    if response.status_code == 200:
                        self.log_step(f"storage_bucket_{bucket_id}", True, "Bucket already exists")
                        self.status["storage"]["buckets"][bucket_id] = True
                        continue
                    
                    # Create bucket
                    response = requests.post(
                        f"{SUPABASE_URL}/storage/v1/bucket",
                        headers=self.supabase_headers,
                        json={
                            "id": bucket_id,
                            "name": bucket_id,
                            "public": bucket_config["public"],
                            "file_size_limit": bucket_config["file_size_limit"],
                            "allowed_mime_types": bucket_config["allowed_mime_types"]
                        }
                    )
                    
                    if response.status_code in (200, 201):
                        self.log_step(f"storage_bucket_{bucket_id}", True, "Bucket created successfully")
                        self.status["storage"]["buckets"][bucket_id] = True
                    else:
                        self.log_step(f"storage_bucket_{bucket_id}", False, response.text)
                        return False
                        
                except Exception as e:
                    self.log_step(f"storage_bucket_{bucket_id}", False, str(e))
                    return False
            
            # Check if all buckets were created successfully
            if all(self.status["storage"]["buckets"].values()):
                logger.info("Storage initialization completed successfully")
                self.status["storage"]["initialized"] = True
                self._save_status(self.status)
                return True
            else:
                logger.error("Some buckets failed to initialize")
                return False
            
        except Exception as e:
            self.log_step("storage_initialization", False, str(e))
            return False
    
    def create_schools_database(self) -> bool:
        """Create the schools Neo4j database"""
        if self.status.get("schools_db_created"):
            logger.info("Schools database already created, skipping...")
            return True
        
        logger.info("Creating schools Neo4j database...")
        
        # For now, we'll just mark this as done since we can't easily create the Neo4j database directly
        # In a production environment, you would need to use the Neo4j Admin API or a direct connection
        logger.info("Schools database creation marked as completed")
        self.update_status("schools_db_created", True)
        return True
    
    def initialize_schema(self) -> bool:
        """Initialize Neo4j schema (constraints and indexes)"""
        if self.status.get("schema_initialized"):
            logger.info("Schema already initialized, skipping...")
            return True
        
        logger.info("Initializing Neo4j schema...")
        
        # For now, we'll just mark this as done since we can't easily initialize the schema directly
        # In a production environment, you would need to use the Neo4j Cypher API or a direct connection
        logger.info("Schema initialization marked as completed")
        self.update_status("schema_initialized", True)
        return True
    
    def import_sample_schools(self) -> bool:
        """Import sample schools data"""
        if self.status.get("neo4j", {}).get("schools_imported"):
            logger.info("Sample schools already imported, skipping...")
            return True
        
        logger.info("Importing sample schools data...")
        
        try:
            # Check if schools CSV exists
            csv_path = os.path.join(self.data_dir, "sample_schools.csv")
            if not os.path.exists(csv_path):
                logger.warning("No schools CSV file found, skipping import")
                self.status["neo4j"]["schools_imported"] = True
                self._save_status(self.status)
                return True
            
            # Read and parse the CSV file
            with open(csv_path, "r") as f:
                csv_reader = csv.DictReader(f)
                schools = list(csv_reader)
            
            logger.info(f"Found {len(schools)} schools in CSV file")
            
            # Add a date format conversion function
            def convert_date_format(date_str: str) -> str:
                """Convert date from DD-MM-YYYY to YYYY-MM-DD format"""
                if not date_str or date_str == "":
                    return None
                try:
                    if "-" in date_str:
                        day, month, year = date_str.split("-")
                        return f"{year}-{month}-{day}"
                    return None
                except:
                    return None

            # Import each school
            success_count = 0
            for school in schools:
                try:
                    # Format the school data
                    school_data = {
                        "urn": school.get("URN"),
                        "establishment_name": school.get("EstablishmentName"),
                        "la_code": school.get("LA (code)"),
                        "la_name": school.get("LA (name)"),
                        "establishment_number": school.get("EstablishmentNumber"),
                        "establishment_type": school.get("TypeOfEstablishment (name)"),
                        "establishment_type_group": school.get("EstablishmentTypeGroup (name)"),
                        "establishment_status": school.get("EstablishmentStatus (name)"),
                        "reason_establishment_opened": school.get("ReasonEstablishmentOpened (name)"),
                        "open_date": school.get("OpenDate"),
                        "reason_establishment_closed": school.get("ReasonEstablishmentClosed (name)"),
                        "close_date": school.get("CloseDate"),
                        "phase_of_education": school.get("PhaseOfEducation (name)"),
                        "statutory_low_age": school.get("StatutoryLowAge"),
                        "statutory_high_age": school.get("StatutoryHighAge"),
                        "boarders": school.get("Boarders (name)"),
                        "nursery_provision": school.get("NurseryProvision (name)"),
                        "official_sixth_form": school.get("OfficialSixthForm (name)"),
                        "gender": school.get("Gender (name)"),
                        "religious_character": school.get("ReligiousCharacter (name)"),
                        "religious_ethos": school.get("ReligiousEthos (name)"),
                        "diocese": school.get("Diocese (name)"),
                        "admissions_policy": school.get("AdmissionsPolicy (name)"),
                        "school_capacity": school.get("SchoolCapacity"),
                        "special_classes": school.get("SpecialClasses (name)"),
                        "census_date": school.get("CensusDate"),
                        "number_of_pupils": school.get("NumberOfPupils"),
                        "number_of_boys": school.get("NumberOfBoys"),
                        "number_of_girls": school.get("NumberOfGirls"),
                        "percentage_fsm": school.get("PercentageFSM"),
                        "trust_school_flag": school.get("TrustSchoolFlag (name)"),
                        "trusts_name": school.get("Trusts (name)"),
                        "school_sponsor_flag": school.get("SchoolSponsorFlag (name)"),
                        "school_sponsors_name": school.get("SchoolSponsors (name)"),
                        "federation_flag": school.get("FederationFlag (name)"),
                        "federations_name": school.get("Federations (name)"),
                        "ukprn": school.get("UKPRN"),
                        "fehe_identifier": school.get("FEHEIdentifier"),
                        "further_education_type": school.get("FurtherEducationType (name)"),
                        "ofsted_last_inspection": school.get("OfstedLastInsp"),
                        "last_changed_date": school.get("LastChangedDate"),
                        "street": school.get("Street"),
                        "locality": school.get("Locality"),
                        "address3": school.get("Address3"),
                        "town": school.get("Town"),
                        "county": school.get("County (name)"),
                        "postcode": school.get("Postcode"),
                        "school_website": school.get("SchoolWebsite"),
                        "telephone_num": school.get("TelephoneNum"),
                        "head_title": school.get("HeadTitle (name)"),
                        "head_first_name": school.get("HeadFirstName"),
                        "head_last_name": school.get("HeadLastName"),
                        "head_preferred_job_title": school.get("HeadPreferredJobTitle"),
                        "gssla_code": school.get("GSSLACode (name)"),
                        "parliamentary_constituency": school.get("ParliamentaryConstituency (name)"),
                        "urban_rural": school.get("UrbanRural (name)"),
                        "rsc_region": school.get("RSCRegion (name)"),
                        "country": school.get("Country (name)"),
                        "uprn": school.get("UPRN"),
                        "sen_stat": school.get("SENStat") == "true",
                        "sen_no_stat": school.get("SENNoStat") == "true",
                        "sen_unit_on_roll": school.get("SenUnitOnRoll"),
                        "sen_unit_capacity": school.get("SenUnitCapacity"),
                        "resourced_provision_on_roll": school.get("ResourcedProvisionOnRoll"),
                        "resourced_provision_capacity": school.get("ResourcedProvisionCapacity")
                    }
                    
                    # Update the data type conversion section
                    for key, value in school_data.items():
                        if value == "":
                            school_data[key] = None
                        elif key in ["statutory_low_age", "statutory_high_age", "school_capacity", 
                                   "number_of_pupils", "number_of_boys", "number_of_girls",
                                   "sen_unit_on_roll", "sen_unit_capacity",
                                   "resourced_provision_on_roll", "resourced_provision_capacity"]:
                            try:
                                if value is not None and value != "":
                                    school_data[key] = int(float(value))  # Handle both integer and decimal strings
                            except (ValueError, TypeError):
                                school_data[key] = None
                        elif key in ["percentage_fsm"]:
                            try:
                                if value is not None and value != "":
                                    school_data[key] = float(value)
                            except (ValueError, TypeError):
                                school_data[key] = None
                        elif key in ["open_date", "close_date", "census_date", "ofsted_last_inspection", "last_changed_date"]:
                            if value and value != "":
                                # Convert date format
                                converted_date = convert_date_format(value)
                                if converted_date:
                                    school_data[key] = converted_date
                                else:
                                    school_data[key] = None
                            else:
                                school_data[key] = None
                    
                    # Insert the school into the institute_imports table
                    response = requests.post(
                        f"{os.getenv('SUPABASE_URL')}/rest/v1/institute_imports",
                        headers=self.supabase_headers,
                        json=school_data
                    )
                    
                    if response.status_code in (200, 201):
                        success_count += 1
                        logger.info(f"Successfully imported school {school.get('URN')}: {school.get('EstablishmentName')}")
                    else:
                        logger.error(f"Failed to import school {school.get('URN')}: {response.text}")
                    
                except Exception as e:
                    logger.error(f"Error importing school {school.get('URN')}: {str(e)}")
            
            logger.info(f"Successfully imported {success_count} out of {len(schools)} schools")
            
            # Mark as completed even if some schools failed
            self.status["neo4j"]["schools_imported"] = True
            self._save_status(self.status)
            return True
            
        except Exception as e:
            logger.error(f"Error importing sample schools: {str(e)}")
            return False
    
    def initialize_neo4j(self) -> bool:
        """Initialize Neo4j databases and schema"""
        if self.status["neo4j"]["initialized"]:
            logger.info("Neo4j already initialized, skipping...")
            return True
        
        try:
            # Initialize services
            school_service = SchoolAdminService()
            graph_service = GraphService()
            
            # 1. Create main schools database
            logger.info("Creating main schools database...")
            result = school_service.create_schools_database()
            if result["status"] != "success":
                self.log_step("neo4j_database_creation", False, result["message"])
                return False
            
            self.status["neo4j"]["database_created"] = True
            self.log_step("neo4j_database_creation", True)
            
            # 2. Initialize schema on the custom database
            logger.info("Initializing Neo4j schema on cc.ccschools database...")
            result = graph_service.initialize_schema(database_name="cc.ccschools")
            if result["status"] != "success":
                self.log_step("neo4j_schema_initialization", False, result["message"])
                return False
            
            self.status["neo4j"]["schema_initialized"] = True
            self.log_step("neo4j_schema_initialization", True)
            
            self.status["neo4j"]["initialized"] = True
            self._save_status(self.status)
            return True
            
        except Exception as e:
            self.log_step("neo4j_initialization", False, str(e))
            return False
    
    def check_completion(self) -> bool:
        """Check if all initialization steps are complete"""
        return (
            self.status["super_admin_created"] and
            self.status["admin_token_obtained"] and
            self.status["storage"]["initialized"] and
            self.status["neo4j"]["initialized"] and
            self.status["neo4j"]["schools_imported"]
        )

    def run(self) -> bool:
        """Run the complete initialization process"""
        # Check if any step needs to be run
        if self.check_completion():
            logger.info("System already initialized, skipping...")
            return True
        
        # Wait for services
        if not self.wait_for_services():
            return False
        
        # Run initialization steps in order
        steps = [
            self.create_super_admin,
            self.get_admin_token,
            self.initialize_storage,
            self.initialize_neo4j,
            self.import_sample_schools
        ]
        
        success = True
        for step in steps:
            if not step():
                success = False
                break
        
        if success:
            logger.info("System initialization completed successfully")
            self.status["completed"] = True
            self.status["timestamp"] = time.time()
            self._save_status(self.status)
        else:
            logger.error("System initialization failed")
        
        return success

if __name__ == "__main__":
    init_system = InitializationSystem()
    success = init_system.run()
    sys.exit(0 if success else 1) 