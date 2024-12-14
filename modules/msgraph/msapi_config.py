from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_msgraph_config'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from msal import ConfidentialClientApplication

CLIENT_ID = os.getenv("VITE_MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("VITE_MICROSOFT_CLIENT_SECRET")
TENANT_ID = os.getenv("VITE_MICROSOFT_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]

# Create an MSAL confidential client application
def get_ms_access_token():
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
    )
    
    # For a confidential client application, we don't use user-specific accounts
    # Instead, we directly acquire a token for the application
    result = app.acquire_token_for_client(scopes=SCOPE)
    
    if 'access_token' in result:
        logging.info("Token acquired successfully")
        return result['access_token']
    else:
        error_message = f"Failed to acquire token: {result.get('error')}, {result.get('error_description')}"
        logging.error(error_message)
        raise Exception(error_message)
