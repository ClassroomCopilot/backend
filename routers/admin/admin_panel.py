import os
from modules.logger_tool import initialise_logger

from supabase import create_client, Client
from modules.auth.supabase_bearer import SupabaseBearer
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Response, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import json
import csv
import io

from modules.database.tools import neontology_tools as neon
from modules.database.schemas import entity_neo
from modules.database.admin.school_manager import SchoolManager
from modules.database.admin.graph_provider import GraphProvider

# Initialize graph provider
graph_provider = GraphProvider()

logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

# Initialize Supabase client with service role key for admin operations
supabase_url = os.getenv("SUPABASE_BACKEND_URL")
service_role_key = os.getenv("SERVICE_ROLE_KEY")
anon_key = os.getenv("ANON_KEY")

logger.info(f"Initializing admin Supabase client with URL: {supabase_url}")
logger.debug(f"Service role key present: {bool(service_role_key)}")

# Create admin client
admin_supabase: Client = create_client(
    supabase_url=supabase_url,
    supabase_key=service_role_key
)

# Set headers for admin operations
admin_supabase.headers = {
    "apiKey": service_role_key,
    "Authorization": f"Bearer {service_role_key}",
    "Content-Type": "application/json",
    "X-Client-Info": "supabase-py/0.0.1"
}

# Set storage client headers explicitly
admin_supabase.storage._client.headers.update({
    "apiKey": service_role_key,
    "Authorization": f"Bearer {service_role_key}",
    "Content-Type": "application/json"
})

# Regular client for non-admin operations
logger.info(f"Initializing regular Supabase client with URL: {supabase_url}")
supabase: Client = create_client(
    supabase_url=supabase_url,
    supabase_key=anon_key
)

# Set headers for regular operations
supabase.headers = {
    "apiKey": anon_key,
    "Authorization": f"Bearer {anon_key}"
}

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
        
        # Create a fresh service role client for this request
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Get user from token using service role client
            user_response = service_client.auth.get_user(access_token)
            user_id = user_response.user.id
            
            logger.debug(f"Verifying admin for user_id: {user_id}")
            
            # Use service role client to check admin profile
            admin_result = service_client.table('admin_profiles').select("*").eq('id', user_id).single().execute()
            
            if not admin_result.data:
                logger.error(f"No admin profile found for user {user_id}")
                raise HTTPException(status_code=403, detail="Not an admin user")
            
            # Log admin data for debugging
            logger.debug(f"Admin data: {admin_result.data}")
            
            # Create a new client with the user's access token for subsequent operations
            user_client = create_client(supabase_url, service_role_key)
            user_client.headers = {
                "apiKey": service_role_key,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Update storage client headers explicitly
            user_client.storage._client.headers.update({
                "apiKey": service_role_key,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            })
            
            # Store the client in the request state for use in other endpoints
            request.state.supabase = user_client
            
            return admin_result.data
            
        except Exception as e:
            logger.error(f"Error verifying admin token: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
    except HTTPException:
        raise
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
            "/dashboard/index.html",
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
            logger.info(f"Checking admin count using Supabase at URL: {supabase_url}")
            admin_count = len(admin_supabase.table("admin_profiles").select("id").execute().data)
            logger.debug(f"Found {admin_count} admins in database")
            if admin_count > 0:
                init_super_admin = False
        except Exception as e:
            logger.error(f"Error checking admin count using Supabase at {supabase_url}: {str(e)}")
            # Continue with the page load even if check fails
    
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
        logger.info(f"Attempting login for email: {email} using Supabase at URL: {supabase_url}")
        
        # Attempt to sign in with Supabase using service role client
        try:
            auth_response = admin_supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            logger.debug("Successfully authenticated with Supabase auth")
        except Exception as auth_error:
            logger.error(f"Authentication failed with Supabase at {supabase_url}: {str(auth_error)}")
            raise HTTPException(status_code=401, detail="Authentication failed")
        
        # Get the user's session
        session = auth_response.session
        user_id = session.user.id
        
        logger.debug(f"Successfully authenticated user: {user_id}")
        
        # Update admin_supabase client headers with the new session token
        admin_supabase.headers.update({
            "Authorization": f"Bearer {session.access_token}",
            "apiKey": anon_key  # Use anon key for authenticated requests
        })
        
        # Update storage client headers explicitly
        admin_supabase.storage._client.headers.update({
            "Authorization": f"Bearer {session.access_token}",
            "apiKey": anon_key
        })
        
        logger.debug("Updated Supabase client headers with new session token")
        
        # Verify the user is an admin using service role client
        try:
            logger.info(f"Checking admin profile for user {user_id} using Supabase at {supabase_url}")
            admin_result = admin_supabase.table('admin_profiles').select("*").eq('id', user_id).single().execute()
            logger.debug(f"Admin profile query result: {admin_result}")
        except Exception as profile_error:
            logger.error(f"Error checking admin profile at {supabase_url}: {str(profile_error)}")
            raise HTTPException(status_code=500, detail="Failed to verify admin status")
        
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
            logger.info(f"Updating last login time for admin {user_id} at {supabase_url}")
            admin_supabase.table('admin_profiles').update({
                "updated_at": "now()"
            }).eq('id', user_id).execute()
        except Exception as update_error:
            logger.warning(f"Failed to update last login time at {supabase_url}: {str(update_error)}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error with Supabase at {supabase_url}: {str(e)}")
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
            supabase_url,
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
        logger.info(f"Using Supabase URL: {supabase_url}")
        
        if not expected_email:
            raise HTTPException(status_code=400, detail="Super admin email not configured")

        # Check if any admin exists
        try:
            logger.info(f"Checking existing admins at {supabase_url}")
            admin_count = len(admin_supabase.table("admin_profiles").select("id").execute().data)
            logger.debug(f"Found {admin_count} existing admins")
            if admin_count > 0:
                raise HTTPException(status_code=400, detail="Super admin already exists")
        except Exception as count_error:
            logger.error(f"Error checking admin count at {supabase_url}: {str(count_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to check existing admins: {str(count_error)}")

        # Create the user with admin metadata
        try:
            logger.info(f"Creating auth user at {supabase_url}")
            auth_user = admin_supabase.auth.admin.create_user({
                "email": admin_data["email"],
                "password": admin_data["password"],
                "email_confirm": True,
                "user_metadata": {
                    "is_admin": True,
                    "is_super_admin": True,
                    "display_name": admin_data["display_name"]
                },
                "app_metadata": {
                    "roles": ["admin", "super_admin"]
                }
            })
            user_id = auth_user.user.id
            logger.debug(f"Created auth user with ID: {user_id}")
        except Exception as auth_error:
            logger.error(f"Error creating auth user at {supabase_url}: {str(auth_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to create auth user: {str(auth_error)}")

        # Create admin profile
        try:
            logger.info(f"Creating admin profile at {supabase_url}")
            profile_result = admin_supabase.table("admin_profiles").insert({
                "id": user_id,
                "email": admin_data["email"],
                "display_name": admin_data["display_name"],
                "admin_role": "admin",
                "is_super_admin": True,
                "metadata": {}
            }).execute()
            logger.debug(f"Admin profile creation result: {profile_result.data}")
        except Exception as profile_error:
            logger.error(f"Error creating admin profile at {supabase_url}: {str(profile_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to create admin profile: {str(profile_error)}")

        return {
            "status": "success",
            "message": "Super admin initialized successfully. Please log in.",
            "data": {
                "email": admin_data["email"],
                "display_name": admin_data["display_name"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing super admin at {supabase_url}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# School management endpoints (only accessible by super admins)
@router.get("/schools/manage", response_class=HTMLResponse)
async def manage_schools(request: Request, admin: dict = Depends(verify_admin)):
    """School management interface"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can manage schools")
        
        # Get list of schools
        schools = admin_supabase.table("schools").select("*").order("establishment_name").execute()
        
        return templates.TemplateResponse(
            "admin/schools_manage.html",
            {
                "request": request,
                "admin": admin,
                "schools": schools.data
            }
        )
    except Exception as e:
        logger.error(f"Error in school management: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schools/import")
async def import_schools(
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin)
):
    """Import schools from CSV file"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can import schools")
        
        # Create a fresh service role client for database operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        
        # Read and validate CSV file
        content = await file.read()
        csv_text = content.decode('utf-8-sig')  # Handle BOM if present
        csv_reader = csv.DictReader(io.StringIO(csv_text))
        
        # Prepare data for batch insert
        schools_data = []
        for row in csv_reader:
            school_data = {
                "urn": row.get("URN"),
                "la_code": row.get("LA (code)"),
                "la_name": row.get("LA (name)"),
                "establishment_number": row.get("EstablishmentNumber"),
                "establishment_name": row.get("EstablishmentName"),
                "establishment_type": row.get("TypeOfEstablishment (name)"),
                "establishment_type_group": row.get("EstablishmentTypeGroup (name)"),
                "establishment_status": row.get("EstablishmentStatus (name)"),
                "reason_establishment_opened": row.get("ReasonEstablishmentOpened (name)"),
                "open_date": row.get("OpenDate"),
                "reason_establishment_closed": row.get("ReasonEstablishmentClosed (name)"),
                "close_date": row.get("CloseDate"),
                "phase_of_education": row.get("PhaseOfEducation (name)"),
                "statutory_low_age": row.get("StatutoryLowAge"),
                "statutory_high_age": row.get("StatutoryHighAge"),
                "boarders": row.get("Boarders (name)"),
                "nursery_provision": row.get("NurseryProvision (name)"),
                "official_sixth_form": row.get("OfficialSixthForm (name)"),
                "gender": row.get("Gender (name)"),
                "religious_character": row.get("ReligiousCharacter (name)"),
                "religious_ethos": row.get("ReligiousEthos (name)"),
                "diocese": row.get("Diocese (name)"),
                "admissions_policy": row.get("AdmissionsPolicy (name)"),
                "school_capacity": row.get("SchoolCapacity"),
                "special_classes": row.get("SpecialClasses (name)"),
                "census_date": row.get("CensusDate"),
                "number_of_pupils": row.get("NumberOfPupils"),
                "number_of_boys": row.get("NumberOfBoys"),
                "number_of_girls": row.get("NumberOfGirls"),
                "percentage_fsm": row.get("PercentageFSM"),
                "trust_school_flag": row.get("TrustSchoolFlag (name)"),
                "trusts_name": row.get("Trusts (name)"),
                "school_sponsor_flag": row.get("SchoolSponsorFlag (name)"),
                "school_sponsors_name": row.get("SchoolSponsors (name)"),
                "federation_flag": row.get("FederationFlag (name)"),
                "federations_name": row.get("Federations (name)"),
                "ukprn": row.get("UKPRN"),
                "fehe_identifier": row.get("FEHEIdentifier"),
                "further_education_type": row.get("FurtherEducationType (name)"),
                "ofsted_last_inspection": row.get("OfstedLastInsp"),
                "last_changed_date": row.get("LastChangedDate"),
                "street": row.get("Street"),
                "locality": row.get("Locality"),
                "address3": row.get("Address3"),
                "town": row.get("Town"),
                "county": row.get("County (name)"),
                "postcode": row.get("Postcode"),
                "school_website": row.get("SchoolWebsite"),
                "telephone_num": row.get("TelephoneNum"),
                "head_title": row.get("HeadTitle (name)"),
                "head_first_name": row.get("HeadFirstName"),
                "head_last_name": row.get("HeadLastName"),
                "head_preferred_job_title": row.get("HeadPreferredJobTitle"),
                "gssla_code": row.get("GSSLACode (name)"),
                "parliamentary_constituency": row.get("ParliamentaryConstituency (name)"),
                "urban_rural": row.get("UrbanRural (name)"),
                "rsc_region": row.get("RSCRegion (name)"),
                "country": row.get("Country (name)"),
                "uprn": row.get("UPRN"),
                "sen_stat": row.get("SENStat") == "true",
                "sen_no_stat": row.get("SENNoStat") == "true",
                "sen_unit_on_roll": row.get("SenUnitOnRoll"),
                "sen_unit_capacity": row.get("SenUnitCapacity"),
                "resourced_provision_on_roll": row.get("ResourcedProvisionOnRoll"),
                "resourced_provision_capacity": row.get("ResourcedProvisionCapacity"),
            }
            
            # Clean up empty strings and convert types
            for key, value in school_data.items():
                if value == "":
                    school_data[key] = None
                elif key in ["statutory_low_age", "statutory_high_age", "school_capacity", 
                           "number_of_pupils", "number_of_boys", "number_of_girls",
                           "sen_unit_on_roll", "sen_unit_capacity",
                           "resourced_provision_on_roll", "resourced_provision_capacity"]:
                    if value:
                        try:
                            float_val = float(value)
                            int_val = int(float_val)
                            school_data[key] = int_val
                        except (ValueError, TypeError):
                            school_data[key] = None
                elif key == "percentage_fsm":
                    if value:
                        try:
                            school_data[key] = float(value)
                        except (ValueError, TypeError):
                            school_data[key] = None
                elif key in ["open_date", "close_date", "census_date", 
                           "ofsted_last_inspection", "last_changed_date"]:
                    if value:
                        try:
                            # Convert date from DD-MM-YYYY to YYYY-MM-DD
                            parts = value.split("-")
                            if len(parts) == 3:
                                school_data[key] = f"{parts[2]}-{parts[1]}-{parts[0]}"
                            else:
                                school_data[key] = None
                        except:
                            school_data[key] = None
            
            schools_data.append(school_data)
        
        # Batch insert schools using service role client
        if schools_data:
            result = service_client.table("schools").upsert(
                schools_data, 
                on_conflict="urn"  # Update if URN already exists
            ).execute()
            
            logger.info(f"Imported {len(schools_data)} schools")
            return {"status": "success", "imported_count": len(schools_data)}
        else:
            raise HTTPException(status_code=400, detail="No valid school data found in CSV")
            
    except Exception as e:
        logger.error(f"Error importing schools: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schools/{school_id}")
async def view_school(
    request: Request,
    school_id: str,
    admin: dict = Depends(verify_admin)
):
    """View school details"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can view school details")
        
        # Get school details
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Get latest statistics
        stats = admin_supabase.table("school_statistics")\
            .select("*")\
            .eq("school_id", school_id)\
            .order("census_date", desc=True)\
            .limit(1)\
            .execute()
        
        return templates.TemplateResponse(
            "admin/school_detail.html",
            {
                "request": request,
                "admin": admin,
                "school": school.data,
                "statistics": stats.data[0] if stats.data else None
            }
        )
    except Exception as e:
        logger.error(f"Error viewing school: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/schools/{school_id}")
async def delete_school(school_id: str, admin: dict = Depends(verify_admin)):
    """Delete a school"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can delete schools")
        
        # Delete school statistics first (due to foreign key constraint)
        await admin_supabase.table("school_statistics").delete().eq("school_id", school_id).execute()
        
        # Delete school
        result = await admin_supabase.table("schools").delete().eq("id", school_id).execute()
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting school: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-schools-database")
async def initialize_schools_database(admin: dict = Depends(verify_admin)):
    """Initialize the cc.ccschools database (super admin only)"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can initialize the schools database")
        
        school_manager = SchoolManager()
        result = school_manager.create_schools_database()
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        
        return result
    except Exception as e:
        logger.error(f"Error initializing schools database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schools/{school_id}/initialize-node")
async def initialize_school_node(
    school_id: str,
    admin: dict = Depends(verify_admin)
):
    """Initialize a school node in the cc.ccschools database"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can initialize school nodes")
        
        # Create a fresh service role client for database operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        
        # Get school data from Supabase using service role client
        school = service_client.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create school manager and verify database exists
        school_manager = SchoolManager()
        
        # Verify cc.ccschools database exists
        try:
            with school_manager.driver.session() as session:
                result = session.run("SHOW DATABASES")
                databases = [record["name"] for record in result]
                if "cc.ccschools" not in databases:
                    logger.error("cc.ccschools database does not exist")
                    raise HTTPException(
                        status_code=500, 
                        detail="Schools database not initialized. Please initialize database first."
                    )
        except Exception as db_error:
            logger.error(f"Error checking database existence: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to verify database existence: {str(db_error)}"
            )
        
        # Create school node using SchoolManager
        try:
            result = school_manager.create_school_node(school.data)
            
            if result["status"] == "error":
                raise Exception(result["message"])
                
            return {
                "status": "success",
                "message": "School node created successfully",
                "node_id": f"School_{school.data['urn']}"
            }
                
        except Exception as node_error:
            logger.error(f"Error creating school node: {str(node_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create school node: {str(node_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing school node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schools/{school_id}/graph-status")
async def check_school_graph_status(
    school_id: str,
    admin: dict = Depends(verify_admin)
):
    """Check if a school node exists in the graph database"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check school graph status")
        
        # Get school data from Supabase
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Check if node exists in Neo4j and get its properties
        school_manager = SchoolManager()
        with school_manager.driver.session(database="cc.ccschools") as session:
            result = session.run(
                """
                MATCH (s:School {unique_id: $unique_id}) 
                RETURN s
                """,
                {"unique_id": f"School_{school.data['urn']}"}
            )
            record = result.single()
            exists = record is not None
            
            # If node exists, get its properties
            node_data = None
            if exists:
                node = record['s']
                node_data = dict(node.items())  # Convert node properties to dict
            
        return {
            "exists": exists,
            "node_data": node_data
        }
    except Exception as e:
        logger.error(f"Error checking school graph status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-schools-database")
async def check_schools_database(admin: dict = Depends(verify_admin)):
    """Check if the cc.ccschools database exists (super admin only)"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check database status")
        
        school_manager = SchoolManager()
        with school_manager.driver.session() as session:
            # Try to list databases
            result = session.run("SHOW DATABASES")
            databases = [record["name"] for record in result]
            exists = "cc.ccschools" in databases
            
        return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking schools database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-storage")
async def check_storage(admin: dict = Depends(verify_admin)):
    """Check status of storage buckets"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check storage status")
        
        try:
            logger.info(f"Checking storage buckets using Supabase at URL: {supabase_url}")
            
            # Create a fresh service role client for storage operations
            service_client = create_client(supabase_url, service_role_key)
            service_client.headers = {
                "apiKey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json"
            }
            service_client.storage._client.headers.update({
                "apiKey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json"
            })
            
            # Define the buckets we want to check
            required_buckets = [
                {
                    "name": "User Files",
                    "id": "cc.ccusers",
                    "exists": False
                },
                {
                    "name": "School Files",
                    "id": "cc.ccschools",
                    "exists": False
                }
            ]
            
            # List buckets and check existence
            all_buckets = service_client.storage.list_buckets()
            existing_bucket_ids = [bucket.id for bucket in all_buckets]
            logger.debug(f"Found buckets via list_buckets: {existing_bucket_ids}")
            
            # Update bucket existence status
            for bucket in required_buckets:
                bucket['exists'] = bucket['id'] in existing_bucket_ids
                logger.debug(f"Bucket {bucket['id']} exists: {bucket['exists']}")
            
            logger.debug(f"Storage check result: required_buckets={required_buckets}")
            
            return {
                "buckets": required_buckets,
                "schema_ready": True
            }
            
        except Exception as e:
            logger.error(f"Error checking storage: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            raise HTTPException(status_code=500, detail=f"Error checking storage: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_storage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-storage")
async def initialize_storage(admin: dict = Depends(verify_admin)):
    """Initialize storage buckets and policies for schools"""
    try:
        # Verify super admin status
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can initialize storage")

        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "X-Client-Info": "supabase-py/0.0.1"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })

        # First, ensure the bucket RLS policy exists
        bucket_policy = """
        -- First, enable RLS on the buckets table if not already enabled
        alter table storage.buckets enable row level security;

        -- Drop existing policies to ensure clean slate
        drop policy if exists "Service role has full access to buckets" on storage.buckets;
        drop policy if exists "Authenticated users can create buckets" on storage.buckets;
        drop policy if exists "Bucket creation requires service role" on storage.buckets;

        -- Create service role policy for full access
        create policy "Service role has full access to buckets"
        on storage.buckets
        as permissive
        for all
        to authenticated
        using (auth.role() = 'service_role')
        with check (auth.role() = 'service_role');
        """

        try:
            # Execute bucket policy using service role client
            service_client.postgrest.rpc('exec_sql', {'query': bucket_policy}).execute()
            logger.info("Successfully created bucket RLS policy")
        except Exception as e:
            logger.warning(f"Bucket policy creation warning (may already exist): {str(e)}")

        # Define buckets to create
        buckets_to_create = [
            {
                "id": "cc.ccusers",
                "name": "User Files",
                "public": False,
                "file_size_limit": 52428800,
                "allowed_mime_types": [
                    'image/*',
                    'video/*',
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'text/plain',
                    'text/csv',
                    'application/json'
                ]
            },
            {
                "id": "cc.ccschools",
                "name": "School Files",
                "public": False,
                "file_size_limit": 52428800,
                "allowed_mime_types": [
                    'image/*',
                    'video/*',
                    'application/pdf',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.ms-excel',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.ms-powerpoint',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'text/plain',
                    'text/csv',
                    'application/json'
                ]
            }
        ]

        # Get list of existing buckets using service role client
        try:
            all_buckets = service_client.storage.list_buckets()
            existing_bucket_ids = [bucket.id for bucket in all_buckets]
            logger.debug(f"Found existing buckets: {existing_bucket_ids}")
        except Exception as e:
            logger.error(f"Error listing buckets: {str(e)}")
            existing_bucket_ids = []

        created_buckets = []
        for bucket in buckets_to_create:
            try:
                if bucket['id'] in existing_bucket_ids:
                    logger.info(f"Bucket {bucket['id']} already exists")
                    created_buckets.append(bucket['id'])
                else:
                    # Create bucket if it doesn't exist using service role client
                    logger.debug(f"Creating bucket {bucket['id']} with options: {bucket}")
                    try:
                        response = service_client.storage.create_bucket(
                            bucket['id'],
                            options={
                                'public': bucket['public'],
                                'file_size_limit': bucket['file_size_limit'],
                                'allowed_mime_types': bucket['allowed_mime_types']
                            }
                        )
                        logger.info(f"Created bucket {bucket['id']}")
                        logger.debug(f"Bucket creation response: {response}")
                        created_buckets.append(bucket['id'])
                    except Exception as bucket_error:
                        logger.error(f"Detailed bucket creation error for {bucket['id']}: {str(bucket_error)}")
                        if hasattr(bucket_error, 'response'):
                            logger.error(f"Error response: {bucket_error.response.text if hasattr(bucket_error.response, 'text') else bucket_error.response}")
                        raise bucket_error
            except Exception as e:
                logger.warning(f"Error with bucket {bucket['id']}: {str(e)}")

        # Create object-level RLS policies
        object_policies = [
            """
            -- Enable RLS on objects table if not already enabled
            alter table storage.objects enable row level security;

            -- Drop existing policies
            drop policy if exists "Users can read own files" on storage.objects;
            drop policy if exists "Users can upload own files" on storage.objects;
            drop policy if exists "Users can update own files" on storage.objects;
            drop policy if exists "Users can delete own files" on storage.objects;
            drop policy if exists "Anyone can read school files" on storage.objects;
            drop policy if exists "Only admins can manage school files" on storage.objects;
            drop policy if exists "Service role has full access to objects" on storage.objects;
            drop policy if exists "Admins can create signed URLs" on storage.objects;

            -- Create user files policies
            create policy "Users can read own files"
                on storage.objects for select
                using (
                    bucket_id = 'cc.ccusers'
                    and (
                        path_tokens[1] = auth.uid()::text
                        or exists (
                            select 1 from auth.users
                            where auth.uid() = auth.users.id
                            and raw_user_meta_data->>'is_admin' = 'true'
                        )
                    )
                );

            create policy "Users can upload own files"
                on storage.objects for insert
                with check (
                    bucket_id = 'cc.ccusers'
                    and path_tokens[1] = auth.uid()::text
                );

            create policy "Users can update own files"
                on storage.objects for update
                using (
                    bucket_id = 'cc.ccusers'
                    and path_tokens[1] = auth.uid()::text
                );

            create policy "Users can delete own files"
                on storage.objects for delete
                using (
                    bucket_id = 'cc.ccusers'
                    and path_tokens[1] = auth.uid()::text
                );

            -- Create school files policies
            create policy "Anyone can read school files"
                on storage.objects for select
                using (bucket_id = 'cc.ccschools');

            create policy "Only admins can manage school files"
                on storage.objects for all
                using (
                    bucket_id = 'cc.ccschools'
                    and (
                        auth.role() = 'service_role'
                        or exists (
                            select 1 from auth.users
                            where auth.uid() = auth.users.id
                            and raw_user_meta_data->>'is_admin' = 'true'
                        )
                    )
                )
                with check (
                    bucket_id = 'cc.ccschools'
                    and (
                        auth.role() = 'service_role'
                        or exists (
                            select 1 from auth.users
                            where auth.uid() = auth.users.id
                            and raw_user_meta_data->>'is_admin' = 'true'
                        )
                    )
                );

            -- Create service role policy
            create policy "Service role has full access to objects"
                on storage.objects for all
                using (auth.role() = 'service_role')
                with check (auth.role() = 'service_role');

            -- Create signed URL policy
            create policy "Admins can create signed URLs"
                on storage.objects for select
                using (
                    exists (
                        select 1 from auth.users
                        where auth.uid() = auth.users.id
                        and raw_user_meta_data->>'is_admin' = 'true'
                    )
                );
            """
        ]

        # Apply object-level policies using service role client
        for policy in object_policies:
            try:
                service_client.postgrest.rpc('exec_sql', {'query': policy}).execute()
                logger.info("Successfully created object RLS policies")
            except Exception as e:
                logger.warning(f"Object policy creation warning (may already exist): {str(e)}")
        
        return {
            "status": "success", 
            "message": "Storage buckets and policies initialized",
            "created_buckets": created_buckets
        }
    except Exception as e:
        logger.error(f"Error initializing storage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage", response_class=HTMLResponse)
async def storage_management(request: Request, admin: dict = Depends(verify_admin)):
    """Storage management interface"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can access storage management")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Get bucket information using storage API
        try:
            logger.info(f"Listing buckets from Supabase storage at URL {supabase_url}")
            buckets = service_client.storage.list_buckets()
            # Convert bucket objects to dictionaries for template
            buckets_data = [{
                'id': bucket.id,
                'name': bucket.name,
                'public': bucket.public,
                'created_at': bucket.created_at,
                'updated_at': bucket.updated_at,
                'file_size_limit': bucket.file_size_limit,
                'allowed_mime_types': bucket.allowed_mime_types
            } for bucket in buckets if bucket.id in ['cc.ccusers', 'cc.ccschools']]
            
            logger.debug(f"Found buckets: {buckets_data}")
            
        except Exception as e:
            logger.error(f"Error getting bucket information: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            buckets_data = []
        
        return templates.TemplateResponse(
            "admin/storage_management.html",
            {
                "request": request,
                "admin": admin,
                "buckets": buckets_data
            }
        )
    except Exception as e:
        logger.error(f"Error in storage management: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/{bucket_id}/contents")
async def list_bucket_contents(
    request: Request,
    bucket_id: str,
    path: str = "",
    admin: dict = Depends(verify_admin)
):
    """List contents of a storage bucket"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can list bucket contents")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Verify bucket exists using storage API
        try:
            logger.info(f"Getting bucket {bucket_id} from Supabase storage at URL {supabase_url}")
            bucket = service_client.storage.get_bucket(bucket_id)
            bucket_data = {
                'id': bucket.id,
                'name': bucket.name,
                'public': bucket.public,
                'created_at': bucket.created_at,
                'updated_at': bucket.updated_at,
                'file_size_limit': bucket.file_size_limit,
                'allowed_mime_types': bucket.allowed_mime_types
            }
            logger.debug(f"Found bucket: {bucket_data}")
        except Exception as e:
            logger.error(f"Error getting bucket {bucket_id}: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            raise HTTPException(status_code=404, detail="Bucket not found")
        
        # List objects in the bucket
        try:
            logger.info(f"Listing files in bucket {bucket_id} at path '{path}'")
            # Use storage API to list files with service role client
            files = service_client.storage.from_(bucket_id).list(path)
            logger.debug(f"Files in bucket {bucket_id}: {files}")
            
            # Organize objects into folders and files
            contents = {
                'folders': set(),
                'files': []
            }
            
            for file in files:
                file_path = file['name']
                if path:
                    # Remove the prefix path if we're in a subfolder
                    if file_path.startswith(path):
                        file_path = file_path[len(path):].lstrip('/')
                
                # Split path into parts
                parts = file_path.split('/')
                
                if len(parts) > 1:
                    # This is in a subfolder
                    contents['folders'].add(parts[0])
                else:
                    # This is a file in the current directory
                    # Add full path back if we're in a subfolder
                    if path:
                        file['name'] = f"{path}/{file_path}"
                    contents['files'].append(file)
            
            contents['folders'] = sorted(list(contents['folders']))
            contents['files'] = sorted(contents['files'], key=lambda x: x['name'])
            
            logger.debug(f"Processed contents: {contents}")
            
        except Exception as e:
            logger.error(f"Error listing bucket contents: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            contents = {'folders': [], 'files': []}
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return contents
        else:
            return templates.TemplateResponse(
                "admin/storage_contents.html",
                {
                    "request": request,
                    "admin": admin,
                    "bucket": bucket_data,
                    "contents": contents,
                    "current_path": path
                }
            )
            
    except Exception as e:
        logger.error(f"Error listing bucket contents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/storage/{bucket_id}/objects/{object_path:path}")
async def delete_object(
    bucket_id: str,
    object_path: str,
    admin: dict = Depends(verify_admin)
):
    """Delete an object from a storage bucket"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can delete objects")
        
        # Delete the object using storage API
        try:
            admin_supabase.storage.from_(bucket_id).remove([object_path])
            return {"status": "success", "message": "Object deleted"}
        except Exception as e:
            logger.error(f"Error deleting object {object_path} from bucket {bucket_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete object: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in delete object handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/manage", response_class=HTMLResponse)
async def manage_school_storage(request: Request, admin: dict = Depends(verify_admin)):
    """School files storage management interface"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can manage storage")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Get list of files from the schools bucket
        try:
            logger.info(f"Listing files from Supabase storage at URL {supabase_url}, bucket: cc.ccschools")
            
            # First, list all root level items
            files = service_client.storage.from_('cc.ccschools').list()
            logger.debug(f"Root level files from Supabase: {files}")
            
            # Process files to ensure we have complete path information
            processed_files = []
            for file in files:
                # Convert file object to dict if it's not already
                if not isinstance(file, dict):
                    file = {
                        'name': file.name,
                        'id': getattr(file, 'id', None),
                        'updated_at': getattr(file, 'updated_at', None),
                        'created_at': getattr(file, 'created_at', None),
                        'last_accessed_at': getattr(file, 'last_accessed_at', None),
                        'metadata': getattr(file, 'metadata', {})
                    }
                
                # Get the school URN from the file path
                school_urn = file['name'].split('/')[0] if '/' in file['name'] else file['name']
                
                # If this is a school URN directory, check for tldraw.json
                if not file['name'].endswith('tldraw.json'):
                    try:
                        # List contents of this folder
                        subfiles = service_client.storage.from_('cc.ccschools').list(school_urn)
                        logger.debug(f"Subfiles for {school_urn}: {subfiles}")
                        
                        for subfile in subfiles:
                            if isinstance(subfile, dict):
                                subfile_name = subfile['name']
                            else:
                                subfile_name = subfile.name
                                
                            if subfile_name.endswith('tldraw.json'):
                                # Get school info for metadata
                                try:
                                    school = service_client.table("schools").select("*").eq("urn", school_urn).single().execute()
                                    metadata = {
                                        "establishment_name": school.data.get("establishment_name"),
                                        "establishment_type": school.data.get("establishment_type")
                                    } if school.data else {}
                                except Exception as school_error:
                                    logger.warning(f"Could not get school info for {school_urn}: {str(school_error)}")
                                    metadata = {}
                                
                                # Add to processed files with full path
                                full_path = f"{school_urn}/{subfile_name}"
                                processed_files.append({
                                    'name': full_path,
                                    'id': getattr(subfile, 'id', None) if not isinstance(subfile, dict) else subfile.get('id'),
                                    'updated_at': getattr(subfile, 'updated_at', None) if not isinstance(subfile, dict) else subfile.get('updated_at'),
                                    'created_at': getattr(subfile, 'created_at', None) if not isinstance(subfile, dict) else subfile.get('created_at'),
                                    'metadata': metadata
                                })
                    except Exception as e:
                        logger.warning(f"Error listing contents of {school_urn}: {str(e)}")
                else:
                    # This is already a tldraw.json file, get its school info
                    school_urn = file['name'].split('/')[0]
                    try:
                        school = service_client.table("schools").select("*").eq("urn", school_urn).single().execute()
                        file['metadata'] = {
                            "establishment_name": school.data.get("establishment_name"),
                            "establishment_type": school.data.get("establishment_type")
                        } if school.data else {}
                    except Exception as school_error:
                        logger.warning(f"Could not get school info for {school_urn}: {str(school_error)}")
                    processed_files.append(file)
            
            logger.debug(f"Processed files: {processed_files}")
            files = processed_files
            
        except Exception as e:
            logger.error(f"Error listing school files: {str(e)}")
            if hasattr(e, 'response'):
                logger.error(f"Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            files = []
        
        return templates.TemplateResponse(
            "admin/storage_manage.html",
            {
                "request": request,
                "admin": admin,
                "files": files
            }
        )
    except Exception as e:
        logger.error(f"Error in storage management: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/{bucket_id}/view/{file_path:path}")
async def view_file(
    request: Request,
    bucket_id: str,
    file_path: str,
    admin: dict = Depends(verify_admin)
):
    """View a file from storage"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can view files")
        
        # Clean up file path and ensure it includes the school URN
        file_path = file_path.strip('/')
        if not '/' in file_path:
            raise HTTPException(status_code=400, detail="Invalid file path. Must include school URN.")
            
        logger.info(f"Attempting to view file from Supabase storage at URL {supabase_url}, bucket: {bucket_id}, path: {file_path}")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Get signed URL for the file
        try:
            # Create signed URL that expires in 1 hour (3600 seconds)
            file_url = service_client.storage.from_(bucket_id).create_signed_url(
                path=file_path,
                expires_in=3600
            )
            
            if not file_url or 'signedURL' not in file_url:
                logger.error(f"Failed to generate signed URL from Supabase at {supabase_url}")
                raise HTTPException(status_code=404, detail="Failed to generate signed URL")
            
            # Replace internal Kong URL with public Supabase URL
            public_url = file_url['signedURL'].replace(
                'http://kong:8000',
                os.getenv('VITE_SUPABASE_URL', 'http://supabase.localhost')
            )
            
            logger.info(f"Successfully generated signed URL from Supabase at {supabase_url}")
            logger.debug(f"Original URL: {file_url['signedURL']}")
            logger.debug(f"Public URL: {public_url}")
            
            return {"url": public_url}
            
        except Exception as e:
            logger.error(f"Error getting signed URL from Supabase at {supabase_url} for {file_path} from bucket {bucket_id}: {str(e)}")
            raise HTTPException(status_code=404, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/{bucket_id}/download/{file_path:path}")
async def download_file(
    request: Request,
    bucket_id: str,
    file_path: str,
    admin: dict = Depends(verify_admin)
):
    """Download a file from storage"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can download files")
        
        # Clean up file path and ensure it includes the school URN
        file_path = file_path.strip('/')
        if not '/' in file_path:
            raise HTTPException(status_code=400, detail="Invalid file path. Must include school URN.")
            
        logger.info(f"Attempting to download file from Supabase storage at URL {supabase_url}, bucket: {bucket_id}, path: {file_path}")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Get signed URL for the file
        try:
            # Create signed URL that expires in 1 hour (3600 seconds)
            file_url = service_client.storage.from_(bucket_id).create_signed_url(
                path=file_path,
                expires_in=3600
            )
            
            if not file_url or 'signedURL' not in file_url:
                logger.error(f"Failed to generate download URL from Supabase at {supabase_url}")
                raise HTTPException(status_code=404, detail="Failed to generate signed URL")
            
            # Replace internal Kong URL with public Supabase URL
            public_url = file_url['signedURL'].replace(
                'http://kong:8000',
                os.getenv('VITE_SUPABASE_URL', 'http://supabase.localhost')
            )
            
            logger.info(f"Successfully generated download URL from Supabase at {supabase_url}")
            logger.debug(f"Original URL: {file_url['signedURL']}")
            logger.debug(f"Public URL: {public_url}")
            
            return {"url": public_url}
            
        except Exception as e:
            logger.error(f"Error getting download URL from Supabase at {supabase_url} for {file_path} from bucket {bucket_id}: {str(e)}")
            raise HTTPException(status_code=404, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/storage/{bucket_id}/upload/{school_urn}")
async def upload_file(
    bucket_id: str,
    school_urn: str,
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin)
):
    """Upload a file to a storage bucket"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can upload files")
        
        # Create a fresh service role client for storage operations
        service_client = create_client(supabase_url, service_role_key)
        service_client.headers = {
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }
        service_client.storage._client.headers.update({
            "apiKey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        })
        
        # Verify bucket exists
        try:
            bucket = service_client.storage.get_bucket(bucket_id)
        except Exception as e:
            logger.error(f"Error getting bucket {bucket_id}: {str(e)}")
            raise HTTPException(status_code=404, detail="Bucket not found")
        
        # Get school data to verify URN and get metadata
        try:
            school = service_client.table("schools").select("*").eq("urn", school_urn).single().execute()
            if not school.data:
                raise HTTPException(status_code=404, detail="School not found")
        except Exception as e:
            logger.error(f"Error getting school data: {str(e)}")
            raise HTTPException(status_code=404, detail="School not found")
        
        # Construct file path
        file_path = f"{school_urn}/tldraw.json"
        
        # Read file content
        content = await file.read()
        
        try:
            # Upload file with metadata
            result = service_client.storage.from_(bucket_id).upload(
                path=file_path,
                file=content,
                file_options={
                    "content-type": "application/json",
                    "x-upsert": "true"  # Update if exists
                }
            )
            
            # Update file metadata
            metadata = {
                "establishment_name": school.data.get("establishment_name"),
                "establishment_type": school.data.get("establishment_type"),
                "size": len(content),
                "mimetype": "application/json"
            }
            
            # Try to update metadata (this might not be supported by all storage providers)
            try:
                service_client.storage.from_(bucket_id).update_file_metadata(
                    path=file_path,
                    metadata=metadata
                )
            except Exception as metadata_error:
                logger.warning(f"Could not update file metadata: {str(metadata_error)}")
            
            return {
                "status": "success",
                "message": "File uploaded successfully",
                "path": file_path
            }
            
        except Exception as upload_error:
            logger.error(f"Error uploading file: {str(upload_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(upload_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload handler: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schools/{school_id}/create-private-database")
async def create_private_database(school_id: str, admin: dict = Depends(verify_admin)):
    """Create private database for school"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can create private databases")
        
        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create school manager and create private database
        school_manager = SchoolManager()
        result = school_manager.create_private_database(school.data)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating private database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schools/{school_id}/create-basic-structure")
async def create_basic_structure(school_id: str, admin: dict = Depends(verify_admin)):
    """Create basic school structure in both public and private databases"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can create school structure")
        
        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create school node
        school_node = entity_neo.SchoolNode(
            unique_id=f"School_{school.data['urn']}",
            path=f"/schools/cc.ccschools/{school.data['urn']}",
            urn=school.data['urn'],
            establishment_number=school.data['establishment_number'],
            establishment_name=school.data['establishment_name'],
            establishment_type=school.data['establishment_type'],
            establishment_status=school.data['establishment_status'],
            phase_of_education=school.data['phase_of_education'] if school.data['phase_of_education'] not in [None, ''] else None,
            statutory_low_age=int(school.data['statutory_low_age']) if school.data.get('statutory_low_age') is not None else 0,
            statutory_high_age=int(school.data['statutory_high_age']) if school.data.get('statutory_high_age') is not None else 0,
            religious_character=school.data.get('religious_character') if school.data.get('religious_character') not in [None, ''] else None,
            school_capacity=int(school.data['school_capacity']) if school.data.get('school_capacity') is not None else 0,
            school_website=school.data.get('school_website', ''),
            ofsted_rating=school.data.get('ofsted_rating') if school.data.get('ofsted_rating') not in [None, ''] else None
        )
        
        # Create school manager
        school_manager = SchoolManager()
        
        # Ensure school node exists in the private database
        with school_manager.neontology as neo:
            # Create/merge in private database
            private_db_name = f"cc.ccschools.{school.data['urn']}"
            neo.create_or_merge_node(school_node, database=private_db_name, operation='merge')
        
        # Create structure in public database
        public_result = school_manager.create_basic_structure(school_node, "cc.ccschools")
        if public_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Error creating public structure: {public_result['message']}")
        
        # Create structure in private database
        private_result = school_manager.create_basic_structure(school_node, private_db_name)
        if private_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Error creating private structure: {private_result['message']}")
        
        return {
            "status": "success",
            "message": "School structure created in both databases",
            "public_result": public_result,
            "private_result": private_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating school structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schools/{school_id}/create-detailed-structure")
async def create_detailed_structure(
    school_id: str,
    file: UploadFile = File(...),
    admin: dict = Depends(verify_admin)
):
    """Create detailed school structure from Excel file"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can create detailed structure")
        
        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create school node
        school_node = entity_neo.SchoolNode(
            unique_id=f"School_{school.data['urn']}",
            urn=school.data['urn'],
            establishment_number=school.data['establishment_number'],
            establishment_name=school.data['establishment_name'],
            establishment_type=school.data['establishment_type'],
            establishment_status=school.data['establishment_status'],
            phase_of_education=school.data['phase_of_education'],
            statutory_low_age=int(school.data['statutory_low_age']) if school.data.get('statutory_low_age') is not None else 0,
            statutory_high_age=int(school.data['statutory_high_age']) if school.data.get('statutory_high_age') is not None else 0,
            religious_character=school.data.get('religious_character') if school.data.get('religious_character') not in [None, ''] else None,
            school_capacity=int(school.data['school_capacity']) if school.data.get('school_capacity') is not None else 0,
            school_website=school.data.get('school_website', ''),
            ofsted_rating=school.data.get('ofsted_rating') if school.data.get('ofsted_rating') not in [None, ''] else None,
            path=f"/schools/cc.ccschools/{school.data['urn']}"
        )
        
        # Read file content
        content = await file.read()
        
        # Create school manager
        school_manager = SchoolManager()
        
        # Create detailed structure in public database
        public_result = school_manager.create_detailed_structure(school_node, "cc.ccschools", content)
        if public_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Error creating public detailed structure: {public_result['message']}")
        
        # Create detailed structure in private database
        private_db_name = f"cc.ccschools.{school.data['urn']}"
        private_result = school_manager.create_detailed_structure(school_node, private_db_name, content)
        if private_result["status"] == "error":
            raise HTTPException(status_code=500, detail=f"Error creating private detailed structure: {private_result['message']}")
        
        return {
            "status": "success",
            "message": "Detailed structure created in both databases",
            "public_result": public_result,
            "private_result": private_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating detailed structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
def check_private_school_database(school_urn):
    """Checks if private database exists for school"""
    try:
        private_db_name = f"cc.ccschools.{school_urn}"
        with graph_provider.neontology as neo:
            result = neo.run_query("SHOW DATABASES", {})
            databases = [record["name"] for record in result]
            exists = private_db_name in databases
            return {"exists": exists}
    except Exception as e:
        logger.error(f"Error checking private database: {str(e)}")
        raise

@router.get("/schools/{school_id}/check-private-school-database")
async def check_private_school_database_endpoint(school_id: str, admin: dict = Depends(verify_admin)):
    """Check if private database exists for school"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check private database")

        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")

        return check_private_school_database(school.data['urn'])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking private database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schools/{school_id}/check-structure-status")
async def check_structure_status(school_id: str, admin: dict = Depends(verify_admin)):
    """Check the structure status for a school in both public and private databases"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check structure status")
        
        # Get basic structure status
        basic_status = await check_basic_structure(school_id, admin)
        
        # Get detailed structure status
        detailed_status = await check_detailed_structure(school_id, admin)
        
        # Combine results
        return {
            "public_database": {
                "basic": basic_status["public_database"],
                "detailed": detailed_status["public_database"]
            },
            "private_database": {
                "exists": basic_status["private_database"]["exists"],
                "basic": basic_status["private_database"]["status"],
                "detailed": detailed_status["private_database"]["status"]
            }
        }
            
    except Exception as e:
        logger.error(f"Error checking structure status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema")
async def schema_page(request: Request, admin: dict = Depends(verify_admin)):
    """Schema management interface"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can manage schema")
            
        return templates.TemplateResponse(
            "admin/schema_details.html",
            {
                "request": request,
                "admin": admin
            }
        )
    except Exception as e:
        logger.error(f"Error in schema management: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-schema")
async def check_schema(admin: dict = Depends(verify_admin)):
    """Check schema status"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check schema")
            
        # Get schema status from both databases
        public_schema = graph_provider.check_schema_status("cc.ccschools")
        
        # Combine results
        combined_schema = {
            "constraints": list(set(public_schema["constraints"])),
            "constraints_count": len(set(public_schema["constraints"])),
            "constraints_valid": public_schema["constraints_valid"],
            
            "indexes": list(set(public_schema["indexes"])),
            "indexes_count": len(set(public_schema["indexes"])),
            "indexes_valid": public_schema["indexes_valid"],
            
            "labels": list(set(public_schema["labels"])),
            "labels_count": len(set(public_schema["labels"])),
            "labels_valid": public_schema["labels_valid"]
        }
        
        return JSONResponse(content=combined_schema)
    except Exception as e:
        logger.error(f"Error checking schema: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/schema-definition")
async def get_schema_definition(admin: dict = Depends(verify_admin)):
    """Get schema definition"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can view schema definition")
            
        schema_info = graph_provider.get_schema_info()
        return JSONResponse(content=schema_info)
    except Exception as e:
        logger.error(f"Error getting schema definition: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/initialize-schema")
async def initialize_schema(admin: dict = Depends(verify_admin)):
    """Initialize schema for both databases"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can initialize schema")
            
        # Initialize schema for both databases
        graph_provider.initialize_schema("cc.ccschools")
        return JSONResponse(content={"message": "Schema initialized successfully"})
    except Exception as e:
        logger.error(f"Error initializing schema: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/schools/{school_id}/check-basic-structure")
async def check_basic_structure(school_id: str, admin: dict = Depends(verify_admin)):
    """Check if basic structure exists for a school"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check structure status")
        
        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create graph provider for Neo4j operations
        provider = GraphProvider()
        
        # Generate the unique ID for the school
        school_unique_id = f"School_{school.data['urn']}"
        
        # Check basic structure in public database
        with provider.neontology as neo:
            basic_query = """
                MATCH (s:School {unique_id: $school_id})
                
                // Get all nodes connected to school for debugging
                CALL {
                    WITH s
                    MATCH (n)
                    WHERE n.unique_id CONTAINS s.unique_id
                    RETURN COLLECT({label: labels(n)[0], id: n.unique_id}) as debug_nodes
                }
                
                // Check Department Structure
                OPTIONAL MATCH (dept_struct:DepartmentStructure)
                WHERE dept_struct.unique_id = $dept_struct_id
                WITH s, debug_nodes, {
                    exists: dept_struct IS NOT NULL,
                    node_id: dept_struct.unique_id
                } as dept_structure
                
                // Check Curriculum Structure
                OPTIONAL MATCH (curr_struct:CurriculumStructure)
                WHERE curr_struct.unique_id = $curr_struct_id
                WITH s, debug_nodes, dept_structure, {
                    exists: curr_struct IS NOT NULL,
                    node_id: curr_struct.unique_id
                } as curr_structure
                
                // Check Pastoral Structure
                OPTIONAL MATCH (past_struct:PastoralStructure)
                WHERE past_struct.unique_id = $past_struct_id
                WITH debug_nodes, dept_structure, curr_structure, {
                    exists: past_struct IS NOT NULL,
                    node_id: past_struct.unique_id
                } as past_structure
                
                // Return structure information
                RETURN {
                    has_basic: dept_structure.exists AND curr_structure.exists AND past_structure.exists,
                    department_structure: dept_structure,
                    curriculum_structure: curr_structure,
                    pastoral_structure: past_structure,
                    debug_nodes: debug_nodes
                } as status
            """
            
            # Use GraphNamingProvider to generate correct IDs
            params = {
                "school_id": school_unique_id,
                "dept_struct_id": f"DepartmentStructure_{school_unique_id}",
                "curr_struct_id": f"CurriculumStructure_{school_unique_id}",
                "past_struct_id": f"PastoralStructure_{school_unique_id}"
            }
            
            # Run query in public database
            public_result = neo.run_query(basic_query, params, "cc.ccschools")
            public_status = public_result[0]["status"] if public_result else {"has_basic": False}
            
            # Check private database if it exists
            private_db_name = f"cc.ccschools.{school.data['urn']}"
            private_exists = False
            private_status = None
            
            # Check if private database exists using Neontology
            db_result = neo.run_query("SHOW DATABASES", {})
            databases = [record["name"] for record in db_result]
            private_exists = private_db_name in databases
            
            if private_exists:
                private_result = neo.run_query(basic_query, params, private_db_name)
                private_status = private_result[0]["status"] if private_result else {"has_basic": False}
            
            return {
                "public_database": public_status,
                "private_database": {
                    "exists": private_exists,
                    "status": private_status if private_exists else None
                }
            }
            
    except Exception as e:
        logger.error(f"Error checking basic structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schools/{school_id}/check-detailed-structure")
async def check_detailed_structure(school_id: str, admin: dict = Depends(verify_admin)):
    """Check if detailed structure exists for a school"""
    try:
        if not admin.get('is_super_admin'):
            raise HTTPException(status_code=403, detail="Only super admins can check structure status")
        
        # Get school data
        school = admin_supabase.table("schools").select("*").eq("id", school_id).single().execute()
        if not school.data:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Create graph provider for Neo4j operations
        provider = GraphProvider()
        
        # Generate the unique ID for the school
        school_unique_id = f"School_{school.data['urn']}"
        
        # Check detailed structure in public database
        with provider.neontology as neo:
            detailed_query = """
                MATCH (s:School {unique_id: $school_id})
                
                // Get all nodes connected to school for debugging
                CALL {
                    WITH s
                    MATCH (n)
                    WHERE n.unique_id CONTAINS s.unique_id
                    RETURN COLLECT({label: labels(n)[0], id: n.unique_id}) as debug_nodes
                }
                
                // Check Department Structure and Departments
                OPTIONAL MATCH (dept_struct:DepartmentStructure)
                WHERE dept_struct.unique_id = $dept_struct_id
                OPTIONAL MATCH (dept:Department)
                WHERE dept.unique_id STARTS WITH 'Department_' + s.unique_id
                WITH s, debug_nodes, {
                    exists: dept_struct IS NOT NULL,
                    has_departments: COUNT(dept) > 0,
                    department_count: COUNT(dept)
                } as dept_structure
                
                // Check Curriculum Structure and Key Stages
                OPTIONAL MATCH (curr_struct:CurriculumStructure)
                WHERE curr_struct.unique_id = $curr_struct_id
                OPTIONAL MATCH (ks:KeyStage)
                WHERE ks.unique_id STARTS WITH 'KeyStage_' + s.unique_id
                WITH s, debug_nodes, dept_structure, {
                    exists: curr_struct IS NOT NULL,
                    has_key_stages: COUNT(ks) > 0,
                    key_stage_count: COUNT(ks)
                } as curr_structure
                
                // Check Pastoral Structure and Year Groups
                OPTIONAL MATCH (past_struct:PastoralStructure)
                WHERE past_struct.unique_id = $past_struct_id
                OPTIONAL MATCH (yg:YearGroup)
                WHERE yg.unique_id STARTS WITH 'YearGroup_' + s.unique_id
                WITH debug_nodes, dept_structure, curr_structure, {
                    exists: past_struct IS NOT NULL,
                    has_year_groups: COUNT(yg) > 0,
                    year_group_count: COUNT(yg)
                } as past_structure
                
                // Return structure information
                RETURN {
                    has_detailed: 
                        dept_structure.exists AND dept_structure.has_departments AND
                        curr_structure.exists AND curr_structure.has_key_stages AND
                        past_structure.exists AND past_structure.has_year_groups,
                    department_structure: dept_structure,
                    curriculum_structure: curr_structure,
                    pastoral_structure: past_structure,
                    debug_nodes: debug_nodes
                } as status
            """
            
            # Use GraphNamingProvider to generate correct IDs
            params = {
                "school_id": school_unique_id,
                "dept_struct_id": f"DepartmentStructure_{school_unique_id}",
                "curr_struct_id": f"CurriculumStructure_{school_unique_id}",
                "past_struct_id": f"PastoralStructure_{school_unique_id}"
            }
            
            # Run query in public database
            public_result = neo.run_query(detailed_query, params, "cc.ccschools")
            public_status = public_result[0]["status"] if public_result else {"has_detailed": False}
            
            # Check private database if it exists
            private_db_name = f"cc.ccschools.{school.data['urn']}"
            private_exists = False
            private_status = None
            
            try:
                with provider.neontology.driver.session() as session:
                    result = session.run("SHOW DATABASES")
                    databases = [record["name"] for record in result]
                    private_exists = private_db_name in databases
                    
                    if private_exists:
                        private_result = neo.run_query(detailed_query, params, private_db_name)
                        private_status = private_result[0]["status"] if private_result else {"has_detailed": False}
            except Exception as e:
                logger.warning(f"Error checking private database: {str(e)}")
            
            return {
                "public_database": public_status,
                "private_database": {
                    "exists": private_exists,
                    "status": private_status if private_exists else None
                }
            }
            
    except Exception as e:
        logger.error(f"Error checking detailed structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Export the router
__all__ = ["router"] 