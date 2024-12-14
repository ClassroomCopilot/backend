from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class HealthCheck(BaseModel):
    """Response model for health check endpoint"""
    status: str = "healthy"

@router.get(
    "/health",
    tags=["Health"],
    summary="Perform a Health Check",
    response_description="Return health status",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck
)
async def health_check() -> HealthCheck:
    """
    Endpoint to perform a healthcheck. Used by container orchestration systems
    to determine if the service is healthy and ready to receive traffic.
    """
    return HealthCheck()