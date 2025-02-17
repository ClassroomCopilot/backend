from fastapi import APIRouter, Depends, HTTPException, Request, Header, Form, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from modules.logger_tool import initialise_logger
from supabase import create_client, Client
from modules.auth.supabase_bearer import SupabaseBearer, verify_supabase_token
import jwt

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

# Initialize Supabase client with service role key for admin operations
admin_supabase: Client = create_client(
    os.getenv("SUPABASE_URL", "http://kong:8000"),
    os.getenv("SERVICE_ROLE_KEY")
)

# Regular client for non-admin operations
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", "http://kong:8000"),
    os.getenv("ANON_KEY")
)

# Use the existing SupabaseBearer for authentication
supabase_auth = SupabaseBearer()

# Admin authentication dependency
async def verify_admin(request: Request):
    """Verify admin status and return admin data"""
    try:
        # Get access token from cookie
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token")
        
        logger.debug("Verifying admin access token")
        
        # Get user from token
        user_response = admin_supabase.auth.get_user(access_token)
        user_id = user_response.user.id
        
        logger.debug(f"Verifying admin for user_id: {user_id}")
        
        # Use service role client to check admin profile
        admin_result = admin_supabase.table('admin_profiles').select("*").eq('id', user_id).single().execute()
        
        if not admin_result.data:
            logger.error(f"No admin profile found for user {user_id}")
            raise HTTPException(status_code=403, detail="Not an admin user")
        
        # Log admin data for debugging
        logger.debug(f"Admin data: {admin_result.data}")
        
        return admin_result.data
    except Exception as e:
        logger.error(f"Admin verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Models for request/response
class UserProfileBase(BaseModel):
    email: str
    display_name: Optional[str] = None
    user_role: Optional[str] = "user"
    is_active: Optional[bool] = True
    metadata: Optional[dict] = {}

class AdminProfileBase(BaseModel):
    email: str
    display_name: Optional[str] = None
    admin_role: Optional[str] = "admin"
    is_super_admin: Optional[bool] = False
    metadata: Optional[dict] = {}

# Setup templates
templates = Jinja2Templates(directory="templates")

# Admin router
router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])

# Serve static files
router.mount("/static", StaticFiles(directory="static"), name="static")

# Admin dashboard
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    access_token = request.cookies.get("access_token")
    if not access_token:
        return RedirectResponse(url="/api/admin/login", status_code=302)
    
    try:
        # Verify token and get user claims using admin client
        user_response = admin_supabase.auth.get_user(access_token)
        user_id = user_response.user.id
        
        # Get admin profile using admin client
        admin = admin_supabase.table('admin_profiles').select('*').eq('id', user_id).single().execute()
        if not admin.data:
            logger.error(f"No admin profile found for user {user_id}")
            response = RedirectResponse(url="/api/admin/login", status_code=302)
            response.delete_cookie("access_token")
            return response

        # Process admin data
        admin_data = admin.data
        # Ensure updated_at is a string
        if admin_data.get('updated_at') and not isinstance(admin_data['updated_at'], str):
            admin_data['updated_at'] = admin_data['updated_at'].isoformat()
            
        logger.debug(f"Admin dashboard data: {admin_data}")
            
        return templates.TemplateResponse(
            "admin/dashboard.html",
            {
                "request": request,
                "admin": admin_data,
                "os": os
            }
        )
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        response = RedirectResponse(url="/api/admin/login", status_code=302)
        response.delete_cookie("access_token")
        return response

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None, success: str = None):
    """Render the login page"""
    # Check if super admin initialization is needed
    init_super_admin = os.getenv("INIT_SUPER_ADMIN", "false").lower() == "true"
    
    if init_super_admin:
        # Check if any admin exists
        try:
            admin_count = len(admin_supabase.table("admin_profiles").select("id").execute().data)
            if admin_count > 0:
                # If admins exist, disable initialization
                init_super_admin = False
                # You might want to update the environment variable here
                # This would require additional setup to modify the .env file
        except Exception as e:
            logger.error(f"Error checking admin count: {str(e)}")
    
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "error": error,
            "success": success,
            "init_super_admin": init_super_admin,
            "expected_super_admin_email": os.getenv("VITE_SUPER_ADMIN_EMAIL")
        }
    )

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle login form submission"""
    try:
        logger.debug(f"Attempting login for email: {email}")
        
        # Attempt to sign in with Supabase using service role client
        auth_response = admin_supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Get the user's session
        session = auth_response.session
        user_id = session.user.id
        
        logger.debug(f"Successfully authenticated user: {user_id}")
        
        # Verify the user is an admin using service role client
        admin_result = admin_supabase.table('admin_profiles').select("*").eq('id', user_id).single().execute()
        
        if not admin_result.data:
            logger.error(f"User {user_id} attempted to log in but is not an admin")
            raise HTTPException(status_code=403, detail="Not an admin user")
        
        admin_data = admin_result.data
        logger.debug(f"Admin profile found: {admin_data}")
        
        # Set the session cookie and redirect
        response = RedirectResponse(url="/api/admin/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=session.access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600  # 1 hour
        )
        
        # Update last login time
        try:
            admin_supabase.table('admin_profiles').update({
                "updated_at": "now()"
            }).eq('id', user_id).execute()
        except Exception as update_error:
            logger.warning(f"Failed to update last login time: {str(update_error)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Invalid email or password"
            },
            status_code=401
        )

@router.post("/logout")
async def logout(response: Response):
    """Handle logout"""
    response = RedirectResponse(url="/api/admin/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

# User management endpoints
@router.get("/users")
async def list_users(request: Request, admin: dict = Depends(verify_admin)):
    """List all users with pagination"""
    try:
        # All admins can view users, no need for super admin check
        users = admin_supabase.table("user_profiles").select("*").execute()
        return templates.TemplateResponse(
            "admin/users.html",
            {"request": request, "users": users.data, "admin": admin}
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}")
async def get_user(request: Request, user_id: str, admin: dict = Depends(verify_admin)):
    """Get user details"""
    try:
        user = admin_supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
        return templates.TemplateResponse(
            "admin/user_detail.html",
            {"request": request, "user": user.data, "admin": admin}
        )
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="User not found")

@router.post("/users/{user_id}")
async def update_user(user_id: str, user: UserProfileBase, admin: dict = Depends(verify_admin)):
    """Update user details"""
    try:
        # All admins can update basic user details
        # But only super admins can modify user roles
        if not admin.get('is_super_admin') and user.user_role != "user":
            raise HTTPException(status_code=403, detail="Only super admins can modify user roles")
            
        updated_user = admin_supabase.table("user_profiles").update(user.dict(exclude_unset=True)).eq("id", user_id).execute()
        return {"status": "success", "data": updated_user.data}
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin management endpoints (only accessible by super admins)
@router.get("/admins")
async def list_admins(request: Request, admin: dict = Depends(verify_admin)):
    """List all admins"""
    try:
        logger.debug(f"Checking admin permissions for admin list. Admin data: {admin}")
        
        # Check if the admin is a super admin
        if not admin.get('is_super_admin'):
            logger.error(f"Non-super admin attempted to access admin list. Admin data: {admin}")
            raise HTTPException(status_code=403, detail="Only super admins can view admin list")
            
        admins = admin_supabase.table("admin_profiles").select("*").execute()
        return templates.TemplateResponse(
            "admin/admins.html",
            {"request": request, "admins": admins.data, "admin": admin}
        )
    except Exception as e:
        logger.error(f"Error listing admins: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admins")
async def create_admin(admin_data: AdminProfileBase, current_admin: dict = Depends(verify_admin)):
    """Create a new admin"""
    try:
        # Special case for first super admin (only if no admins exist)
        admin_count = len(admin_supabase.table("admin_profiles").select("id").execute().data)
        is_first_admin = admin_count == 0
        
        # Only allow super admin creation by existing super admins (except for first admin)
        if admin_data.is_super_admin and not is_first_admin and not current_admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can create super admins")
        
        # For security, ensure email matches the expected super admin email for first admin
        if is_first_admin:
            expected_super_admin_email = os.getenv("VITE_SUPER_ADMIN_EMAIL")
            if not expected_super_admin_email or admin_data.email != expected_super_admin_email:
                raise HTTPException(status_code=403, detail="Invalid super admin email")
            admin_data.is_super_admin = True  # Force first admin to be super admin
        elif not current_admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can create new admins")
        
        # Create auth user with admin metadata
        user_data = {
            "email": admin_data.email,
            "password": os.urandom(16).hex(),  # Generate random password
            "email_confirm": True,
            "user_metadata": {
                "is_admin": True,
                "is_super_admin": admin_data.is_super_admin
            }
        }
        
        # Use supabase auth admin API with service role key for admin creation
        service_role_client = create_client(
            os.getenv("SUPABASE_URL", "http://kong:8000"),
            os.getenv("SERVICE_ROLE_KEY")
        )
        auth_user = service_role_client.auth.admin.create_user(user_data)
        
        # Create admin profile
        admin_profile = admin_data.dict()
        admin_profile["id"] = auth_user.user.id
        
        new_admin = admin_supabase.table("admin_profiles").insert(admin_profile).execute()
        
        # Send password reset email to new admin
        service_role_client.auth.admin.generate_link({
            "type": "recovery",
            "email": admin_data.email
        })
        
        return {"status": "success", "data": new_admin.data}
    except Exception as e:
        logger.error(f"Error creating admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-super-admin/{user_id}")
async def setup_super_admin(user_id: str):
    """Set up the initial super admin user"""
    try:
        # Get the expected super admin email from environment
        expected_email = os.getenv("VITE_SUPER_ADMIN_EMAIL")
        
        # Get user details
        user_response = admin_supabase.auth.admin.get_user_by_id(user_id)
        user = user_response.user
        
        if not user or user.email != expected_email:
            raise HTTPException(status_code=403, detail="Unauthorized to become super admin")
        
        # Update user metadata using auth admin API
        updated_user = admin_supabase.auth.admin.update_user_by_id(
            user_id,
            user_attributes={
                "user_metadata": {
                    "is_admin": True,
                    "is_super_admin": True
                },
                "app_metadata": {
                    "roles": ["admin", "super_admin"]
                }
            }
        )
        
        # Create or update admin profile
        admin_profile = {
            "id": user_id,
            "email": user.email,
            "display_name": "Super Admin",
            "admin_role": "admin",
            "is_super_admin": True,
            "metadata": {}
        }
        
        profile_result = admin_supabase.table("admin_profiles").upsert(admin_profile).execute()
        
        return {
            "status": "success",
            "message": "Super admin setup completed",
            "data": profile_result.data
        }
        
    except Exception as e:
        logger.error(f"Error setting up super admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-super-admin")
async def initialize_super_admin(admin_data: dict):
    """Initialize the first super admin user with form data"""
    try:
        # Get the expected super admin email from environment
        expected_email = os.getenv("VITE_SUPER_ADMIN_EMAIL")
        is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        
        logger.debug(f"Initializing super admin with data: {admin_data}")
        
        if not expected_email:
            raise HTTPException(status_code=400, detail="Super admin email not configured")

        # Check if any admin exists
        admin_count = len(admin_supabase.table("admin_profiles").select("id").execute().data)
        if admin_count > 0:
            raise HTTPException(status_code=400, detail="Super admin already exists")

        # Verify the email matches the expected super admin email
        if admin_data["email"] != expected_email:
            raise HTTPException(status_code=403, detail="Invalid super admin email")

        # Ensure display_name is present
        if "display_name" not in admin_data or not admin_data["display_name"]:
            admin_data["display_name"] = "Super Admin"  # Default fallback
        
        logger.debug(f"Using display name: {admin_data['display_name']}")

        # Create the user with admin metadata
        user_data = {
            "email": admin_data["email"],
            "password": admin_data["password"],
            "email_confirm": True,
            "user_metadata": {
                "is_admin": True,
                "is_super_admin": True,
                "display_name": admin_data["display_name"]  # Add to metadata
            },
            "app_metadata": {
                "roles": ["admin", "super_admin"]
            }
        }

        # Create the user using auth admin API
        auth_user = admin_supabase.auth.admin.create_user(user_data)
        user_id = auth_user.user.id

        logger.debug(f"Created auth user with ID: {user_id}")

        # Create admin profile
        admin_profile = {
            "id": user_id,
            "email": admin_data["email"],
            "display_name": admin_data["display_name"],
            "admin_role": "admin",
            "is_super_admin": True,
            "metadata": {}
        }

        logger.debug(f"Creating admin profile with data: {admin_profile}")

        # Insert admin profile
        profile_result = admin_supabase.table("admin_profiles").insert(admin_profile).execute()
        
        logger.debug(f"Admin profile creation result: {profile_result.data}")

        # Verify the profile was created correctly
        created_profile = admin_supabase.table("admin_profiles").select("*").eq("id", user_id).single().execute()
        logger.debug(f"Verified created profile: {created_profile.data}")

        # Prepare response
        response_data = {
            "status": "success",
            "message": "Super admin initialized successfully. Please log in.",
            "data": {
                "email": admin_data["email"],
                "display_name": admin_data["display_name"]
            }
        }

        return response_data

    except Exception as e:
        logger.error(f"Error initializing super admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Template for the base admin layout
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClassroomCopilot Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <nav class="bg-gray-800 text-white p-4">
        <div class="container mx-auto">
            <div class="flex justify-between items-center">
                <div>
                    <h1 class="text-xl font-bold">ClassroomCopilot Admin</h1>
                    <div class="mt-2">
                        <a href="/api/admin" class="mr-4">Dashboard</a>
                        <a href="/api/admin/users" class="mr-4">Users</a>
                        <a href="/api/admin/admins" class="mr-4">Admins</a>
                    </div>
                </div>
                {% if request.url.path != '/api/admin/login' %}
                <form action="/api/admin/logout" method="POST" class="mt-2">
                    <button type="submit" class="text-white hover:text-gray-300">
                        Logout
                    </button>
                </form>
                {% endif %}
            </div>
        </div>
    </nav>
    <main class="container mx-auto mt-8">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""

# Create templates directory and base template
os.makedirs("templates/admin", exist_ok=True)
with open("templates/admin/base.html", "w") as f:
    f.write(BASE_TEMPLATE)

# Export the router
__all__ = ["router"] 