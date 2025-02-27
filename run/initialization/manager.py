"""
Initialization manager for ClassroomCopilot
"""
import os
import json
from typing import Dict
import requests

from modules.logger_tool import initialise_logger

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

class InitializationManager:
    def __init__(self):
        self.init_dir = "/init"
        self.status_file = os.path.join(self.init_dir, "status.json")
        self.data_dir = os.path.join(self.init_dir, "data")
        
        # Ensure directories exist
        os.makedirs(self.init_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.supabase_headers = {
            "apikey": os.getenv("SERVICE_ROLE_KEY"),
            "Authorization": f"Bearer {os.getenv('SERVICE_ROLE_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Define default status structure
        self.default_status = {
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
        
        self.status = self._load_status()

    def _load_status(self) -> Dict:
        """Load or create initialization status"""
        try:
            with open(self.status_file, "r") as f:
                status = json.load(f)
            
            # Update with any missing keys
            def update_dict(current: Dict, default: Dict) -> Dict:
                for key, value in default.items():
                    if key not in current:
                        current[key] = value
                    elif isinstance(value, dict) and isinstance(current[key], dict):
                        current[key] = update_dict(current[key], value)
                return current
            
            status = update_dict(status, self.default_status)
            self._save_status(status)
            return status
            
        except (FileNotFoundError, json.JSONDecodeError):
            self._save_status(self.default_status)
            return self.default_status.copy()

    def _save_status(self, status: Dict) -> None:
        """Save status to file"""
        os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
        with open(self.status_file, "w") as f:
            json.dump(status, f, indent=2)

    def check_admin_exists(self) -> bool:
        """Check if super admin already exists"""
        try:
            response = requests.get(
                f"{os.getenv('SUPABASE_URL')}/auth/v1/admin/users",
                headers=self.supabase_headers
            )
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            # Fix: response format is {'users': [...], 'aud': 'authenticated'}
            users = data.get('users', [])
            if not isinstance(users, list):
                logger.error(f"Unexpected users format: {users}")
                return False
                
            admin_email = os.getenv('ADMIN_EMAIL')
            
            # Check for admin in users
            admin_user = next(
                (user for user in users 
                 if user.get("email") == admin_email 
                 and user.get("app_metadata", {}).get("role") == "supabase_admin"),
                None
            )
            
            if admin_user:
                logger.info(f"Super admin {admin_email} already exists")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking admin existence: {str(e)}")
            return False

    def check_initialization_needed(self) -> bool:
        """Check if initialization is needed"""
        # First check if admin exists
        if self.check_admin_exists():
            logger.info("Super admin exists, skipping initialization")
            return False
            
        # Then check status file
        if self.status.get("completed"):
            logger.info("Initialization already completed")
            return False
            
        # Check if any step needs completion
        incomplete = not all(
            v for k, v in self.status.items() 
            if k not in ("timestamp", "steps")
        )
        
        if incomplete:
            logger.info("Incomplete initialization detected")
            return True
            
        return False 