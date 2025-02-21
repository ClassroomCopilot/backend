import os
from typing import Dict, List, Optional
from supabase import create_client
from modules.logger_tool import initialise_logger
from pydantic import BaseModel

class AdminProfileBase(BaseModel):
    email: str
    display_name: Optional[str] = None
    admin_role: Optional[str] = "admin"
    is_super_admin: Optional[bool] = False
    metadata: Optional[dict] = {}

class AdminService:
    def __init__(self):
        self.logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
        
        # Initialize Supabase client with service role key
        supabase_url = os.getenv("SUPABASE_BACKEND_URL")
        service_role_key = os.getenv("SERVICE_ROLE_KEY")
        
        self.supabase = create_client(supabase_url, service_role_key)
        
        # Set headers for admin operations
        self.supabase.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }

    def get_admin_profile(self, admin_id: str) -> Optional[Dict]:
        """Get admin profile by ID"""
        try:
            self.logger.info(f"Getting admin profile for ID: {admin_id}")
            result = self.supabase.table("admin_profiles").select("*").eq("id", admin_id).single().execute()
            return result.data if result else None
        except Exception as e:
            self.logger.error(f"Error getting admin profile: {str(e)}")
            raise

    def list_admins(self) -> List[Dict]:
        """List all admin profiles"""
        try:
            self.logger.info("Listing all admin profiles")
            result = self.supabase.table("admin_profiles").select("*").execute()
            return result.data if result else []
        except Exception as e:
            self.logger.error(f"Error listing admins: {str(e)}")
            raise

    def create_admin(self, admin_data: AdminProfileBase, current_admin: Dict) -> Dict:
        """Create a new admin profile"""
        try:
            # Verify super admin status
            if not current_admin.get("is_super_admin"):
                raise Exception("Only super admins can create new admins")

            self.logger.info(f"Creating new admin profile for email: {admin_data.email}")
            
            # Create auth user first
            auth_user = self.supabase.auth.admin.create_user({
                "email": admin_data.email,
                "email_confirm": True,
                "user_metadata": {"is_admin": True}
            })

            if not auth_user:
                raise Exception("Failed to create auth user")

            # Create admin profile
            profile_data = admin_data.dict()
            profile_data["id"] = auth_user.id

            result = self.supabase.table("admin_profiles").insert(profile_data).execute()
            return result.data[0] if result else None

        except Exception as e:
            self.logger.error(f"Error creating admin: {str(e)}")
            raise

    def update_admin(self, admin_id: str, admin_data: AdminProfileBase, current_admin: Dict) -> Dict:
        """Update an admin profile"""
        try:
            # Verify super admin status for certain operations
            if admin_data.is_super_admin and not current_admin.get("is_super_admin"):
                raise Exception("Only super admins can modify super admin status")

            self.logger.info(f"Updating admin profile for ID: {admin_id}")
            result = self.supabase.table("admin_profiles").update(admin_data.dict()).eq("id", admin_id).execute()
            return result.data[0] if result else None

        except Exception as e:
            self.logger.error(f"Error updating admin: {str(e)}")
            raise

    def delete_admin(self, admin_id: str, current_admin: Dict) -> None:
        """Delete an admin profile"""
        try:
            # Verify super admin status
            if not current_admin.get("is_super_admin"):
                raise Exception("Only super admins can delete admins")

            # Get admin profile to check if it's a super admin
            admin_profile = self.get_admin_profile(admin_id)
            if admin_profile and admin_profile.get("is_super_admin"):
                raise Exception("Cannot delete super admin accounts")

            self.logger.info(f"Deleting admin profile for ID: {admin_id}")
            
            # Delete auth user
            self.supabase.auth.admin.delete_user(admin_id)
            
            # Delete admin profile
            self.supabase.table("admin_profiles").delete().eq("id", admin_id).execute()

        except Exception as e:
            self.logger.error(f"Error deleting admin: {str(e)}")
            raise

    def setup_super_admin(self, admin_data: dict) -> Dict:
        """Set up the initial super admin account"""
        try:
            self.logger.info(f"Setting up super admin for email: {admin_data['email']}")
            
            # Check if any super admin exists
            existing_super_admin = self.supabase.table("admin_profiles").select("*").eq("is_super_admin", True).execute()
            if existing_super_admin.data:
                raise Exception("Super admin already exists")

            # Create the auth user first
            auth_user = self.supabase.auth.admin.create_user({
                "email": admin_data["email"],
                "password": admin_data["password"],
                "email_confirm": True,
                "user_metadata": {
                    "is_admin": True,
                    "is_super_admin": True
                }
            })

            if not auth_user:
                raise Exception("Failed to create auth user")

            # Update user metadata
            self.supabase.auth.admin.update_user_by_id(
                auth_user.user.id,
                {"user_metadata": {"is_admin": True, "is_super_admin": True}}
            )

            # Create super admin profile
            profile_data = {
                "id": auth_user.user.id,
                "email": admin_data["email"],
                "display_name": admin_data.get("display_name", "Super Admin"),
                "admin_role": "super_admin",
                "is_super_admin": True
            }

            result = self.supabase.table("admin_profiles").insert(profile_data).execute()
            return result.data[0] if result else None

        except Exception as e:
            self.logger.error(f"Error setting up super admin: {str(e)}")
            raise
