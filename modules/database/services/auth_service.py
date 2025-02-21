import os
from typing import Dict, Optional
from fastapi import HTTPException
from supabase import create_client, Client
from modules.logger_tool import initialise_logger

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

class AuthService:
    def __init__(self):
        """Initialize the AuthService with Supabase clients"""
        self.supabase_url = os.getenv("SUPABASE_BACKEND_URL")
        self.anon_key = os.getenv("ANON_KEY")
        self.service_role_key = os.getenv("SERVICE_ROLE_KEY")
        
        # Create clients with different access levels
        self.supabase: Client = create_client(self.supabase_url, self.anon_key)
        self.admin_supabase: Client = create_client(self.supabase_url, self.service_role_key)

    async def verify_admin(self, session_token: str) -> Dict:
        """Verify that the user is an admin and has necessary permissions"""
        try:
            if not session_token:
                raise HTTPException(status_code=401, detail="Not authenticated")

            # Verify session with Supabase
            user = self.admin_supabase.auth.get_user(session_token)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid session")

            # Get admin profile
            admin = self.admin_supabase.table("admin_profiles").select("*").eq("id", user.user.id).single().execute()
            if not admin.data:
                raise HTTPException(status_code=403, detail="Not an admin")

            return admin.data

        except Exception as e:
            logger.error(f"Error verifying admin: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    async def check_super_admin_exists(self) -> bool:
        """Check if any super admin exists in the system"""
        try:
            result = self.admin_supabase.table("admin_profiles").select("*").eq("is_super_admin", True).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error checking super admin: {str(e)}")
            return False

    async def login_admin(self, email: str, password: str) -> Dict:
        """Handle admin login and return session data"""
        try:
            # Attempt login with Supabase
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not auth_response.user:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Verify admin status
            admin = self.admin_supabase.table("admin_profiles").select("*").eq("id", auth_response.user.id).single().execute()
            if not admin.data:
                raise HTTPException(status_code=403, detail="Not authorized as admin")

            return {
                "access_token": auth_response.session.access_token,
                "admin": admin.data
            }

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(status_code=401, detail=str(e))

# Create a singleton instance
auth_service = AuthService()
