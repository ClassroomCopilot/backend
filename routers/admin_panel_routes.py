from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from modules.logger_tool import initialise_logger
from modules.database.services.school_admin_service import SchoolAdminService
from modules.database.supabase.utils.storage import StorageManager
from .auth import verify_admin
from typing import Dict

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

# Initialize services
school_service = SchoolAdminService()
storage_manager = StorageManager()

@router.get("/schools/manage", response_class=HTMLResponse)
async def manage_schools(request: Request, admin: Dict = Depends(verify_admin)):
    """Manage schools page"""
    return templates.TemplateResponse(
        "admin/schools/manage.html",
        {"request": request, "admin": admin}
    )

@router.get("/storage/manage", response_class=HTMLResponse)
async def manage_storage(request: Request, admin: Dict = Depends(verify_admin)):
    """Storage management page"""
    try:
        # Get list of storage buckets with correct IDs
        buckets = [
            {
                "id": "cc.ccschools",
                "name": "School Files",
                "public": False,
                "file_size_limit": 50 * 1024 * 1024,  # 50MB
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
                "id": "cc.ccusers",
                "name": "User Files",
                "public": False,
                "file_size_limit": 50 * 1024 * 1024,  # 50MB
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
        
        return templates.TemplateResponse(
            "admin/storage/manage.html",
            {"request": request, "admin": admin, "buckets": buckets}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema", response_class=HTMLResponse)
async def manage_schema(request: Request, admin: Dict = Depends(verify_admin)):
    """Schema management page"""
    return templates.TemplateResponse(
        "admin/schema/manage.html",
        {"request": request, "admin": admin}
    )

@router.get("/storage/{bucket_id}/contents")
async def list_bucket_contents(
    request: Request,
    bucket_id: str,
    path: str = "",
    admin: Dict = Depends(verify_admin)
):
    """List contents of a storage bucket"""
    try:
        contents = storage_manager.list_bucket_contents(bucket_id, path)
        bucket = {"id": bucket_id, "name": bucket_id.replace("_", " ").title()}
        
        return templates.TemplateResponse(
            "admin/storage/contents.html",
            {
                "request": request,
                "admin": admin,
                "bucket": bucket,
                "contents": contents,
                "current_path": path
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
