from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_msgraph_client'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import requests

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

class MSGraphClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_onenote_notebooks(self):
        url = f"{GRAPH_API_ENDPOINT}/me/onenote/notebooks"
        response = requests.get(url, headers=self.get_headers())

        if response.status_code == 200:
            return response.json().get('value', [])
        else:
            raise Exception(f"Error fetching notebooks: {response.status_code}, {response.text}")

# Function to initialize the MSGraph client
def get_msgraph_client(access_token: str):
    return MSGraphClient(access_token)
