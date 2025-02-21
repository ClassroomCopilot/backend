from fastapi import APIRouter, Request, Response, HTTPException, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
import os
from modules.logger_tool import initialise_logger
from modules.database.services.admin_service import AdminService
from modules.database.services.auth_service import auth_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

# Initialize services
admin_service = AdminService()

async def verify_admin(request: Request) -> Dict:
    """Verify that the user is an admin and has necessary permissions"""
    session = request.cookies.get("sb-access-token")
    return await auth_service.verify_admin(session)

@router.get("/admin", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Root admin route - redirects to login or dashboard"""
    try:
        admin = await verify_admin(request)
        return RedirectResponse(url="/api/admin/", status_code=303)
    except HTTPException:
        # Check if super admin exists
        has_super_admin = await auth_service.check_super_admin_exists()
        if not has_super_admin:
            return RedirectResponse(url="/api/admin/login?init=true", status_code=303)
        return RedirectResponse(url="/api/admin/login", status_code=303)

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str = None,
    success: str = None,
    init: bool = False
):
    """Render admin login page"""
    # Check if super admin exists
    has_super_admin = await auth_service.check_super_admin_exists()
    
    # If no super admin and init flag is true, show initialization form
    if not has_super_admin:
        expected_email = os.getenv("VITE_SUPER_ADMIN_EMAIL")
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": error,
                "success": success,
                "init_super_admin": True,
                "expected_super_admin_email": expected_email
            }
        )
    
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "error": error,
            "success": success,
            "init_super_admin": False
        }
    )

@router.post("/admin/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle admin login"""
    try:
        # Login with auth service
        auth_result = await auth_service.login_admin(email, password)
        
        # Set session cookie and redirect
        response = RedirectResponse(url="/api/admin/", status_code=303)
        response.set_cookie(
            "sb-access-token",
            auth_result["access_token"],
            httponly=True,
            secure=True
        )
        return response

    except HTTPException as e:
        return RedirectResponse(
            url=f"/api/admin/login?error={str(e.detail)}",
            status_code=303
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return RedirectResponse(
            url=f"/api/admin/login?error={str(e)}",
            status_code=303
        )

@router.post("/admin/logout")
async def logout(response: Response):
    """Handle admin logout"""
    try:
        response = RedirectResponse(url="/api/admin/login", status_code=303)
        response.delete_cookie("sb-access-token")
        return response
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.post("/admin/initialize-super-admin")
async def initialize_super_admin(
    admin_data: Dict = Body(...),
    request: Request = None
):
    """Initialize the super admin account"""
    try:
        # Validate required fields
        required_fields = ["email", "password", "display_name"]
        for field in required_fields:
            if field not in admin_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Set up super admin
        admin_service = AdminService()
        result = admin_service.setup_super_admin(admin_data)
        
        return {
            "status": "success",
            "message": "Super admin account created successfully! Please log in with your credentials.",
            "admin": result
        }
    except Exception as e:
        logger.error(f"Error initializing super admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
