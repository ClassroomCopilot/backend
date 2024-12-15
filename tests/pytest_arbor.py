import os
import requests
import pytest
import json

# Define the base URL and the tokens
base_url = f"http://{os.environ.get('HOST_BACKEND')}:{os.environ.get('PORT_BACKEND')}/arbor/data"
tokens = {
    1: os.getenv("KS3_COURSE_CLASS_MEMBERSHIP_AUTH"),
    2: os.getenv("TEACHING_GROUP_MEMBERSHIPS_2023_2024_AUTH"),
    3: os.getenv("SCHEDULED_TIMETABLE_SLOTS_AUTH"),
    4: os.getenv("BEHAVIOURAL_INCIDENTS_REPORTING_AUTH"),
    5: os.getenv("Y7_LESSON_TIMETABLE_AUTH")
}

@pytest.mark.parametrize("id", [1, 2, 3, 4, 5])
def test_fetch_arbor_data(id):
    token = tokens.get(id)
    if not token:
        pytest.fail(f"Token for ID {id} is not set")
    
    endpoint = f"{base_url}/{id}"
    headers = {"Authorization": f"Basic {token}"}
    params = {"token": token}
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        print(json.dumps(response.json()))
        assert response.status_code == 200
    else:
        pytest.fail(f"Failed for ID {id}: {response.status_code} {response.text}")

