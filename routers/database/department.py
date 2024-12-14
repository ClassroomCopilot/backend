from fastapi import APIRouter, Depends, File, UploadFile
from backend.app.run.dependencies import admin_dependency

router = APIRouter()
