from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
import os

router = APIRouter()

class LoginRequest(BaseModel):
    device_id: str

@router.post("/login")
async def rpi_login(request: LoginRequest):
    if request.device_id == "rpi_zero":
        token = jwt.encode({"device_id": request.device_id}, os.getenv("FASTAPI_SECRET_KEY"), algorithm="HS256")
        return {"token": token}
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
