from fastapi import APIRouter, HTTPException
import os
import requests
from base64 import b64decode

router = APIRouter()

def get_basic_auth_header(token: str) -> dict:
    """Decode the base64 token and return the appropriate header."""
    decoded_token = b64decode(token).decode('utf-8')
    return {"Authorization": f"Basic {token}"}

@router.get("/data/{id}")
async def fetch_arbor_data(id: int, token: str):
    url_mapping = {
        1: os.environ["KS3_COURSE_CLASS_MEMBERSHIP_URL"],
        2: os.environ["TEACHING_GROUP_MEMBERSHIPS_2023_2024_URL"],
        3: os.environ["SCHEDULED_TIMETABLE_SLOTS_URL"],
        4: os.environ["BEHAVIOURAL_INCIDENTS_REPORTING_URL"],
        5: os.environ["Y7_LESSON_TIMETABLE_URL"]
    }
    if id not in url_mapping:
        raise HTTPException(status_code=404, detail="Data ID not supported")

    headers = get_basic_auth_header(token)
    response = requests.get(url_mapping[id], headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from Arbor")
    return response.json()
