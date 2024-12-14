from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_router_onenote'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter, Header, HTTPException
import httpx
import aiohttp

MICROSOFT_GRAPH_API = "https://graph.microsoft.com/v1.0"

router = APIRouter()

@router.get("/test-microsoft-graph-connection")
async def test_microsoft_graph_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MICROSOFT_GRAPH_API}/$metadata") as response:
                if response.status == 200:
                    return {"status": "success", "message": "Successfully connected to Microsoft Graph API"}
                else:
                    return {"status": "error", "message": f"Failed to connect to Microsoft Graph API. Status code: {response.status}"}
    except Exception as e:
        logging.error(f"Error testing connection to Microsoft Graph API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error testing connection to Microsoft Graph API: {str(e)}")

@router.get("/onenote/get-onenote-notebooks")
async def get_onenote_notebooks(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        access_token = token
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    get_notebooks_url = f"{MICROSOFT_GRAPH_API}/me/onenote/notebooks"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(get_notebooks_url, headers=headers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error making request to Microsoft Graph API: {str(e)}")

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f"Error getting notebooks: {response.text}")
    
@router.post("/onenote/create-onenote-notebook")
async def create_onenote_notebook(notebook_name: str, authorization: str = Header(None)):
    logging.info(f"Received request to create notebook: {notebook_name}")
    if not authorization:
        logging.error("Authorization token missing")
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            logging.error(f"Invalid authentication scheme: {scheme}")
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        access_token = token
    except ValueError:
        logging.error("Invalid token format")
        raise HTTPException(status_code=401, detail="Invalid token format")

    # logging.debug(f"Extracted access token: {access_token}")  
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    create_notebook_url = f"{MICROSOFT_GRAPH_API}/me/onenote/notebooks"
    notebook_data = {
        "displayName": notebook_name
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logging.debug(f"Sending request to: {create_notebook_url}")
            logging.debug(f"Headers: {headers}")
            logging.debug(f"Data: {notebook_data}")
            response = await client.post(create_notebook_url, headers=headers, json=notebook_data)
            logging.debug(f"Microsoft Graph API response status: {response.status_code}")
            logging.debug(f"Microsoft Graph API response content: {response.text}")
        except httpx.ConnectTimeout:
            logging.error("Connection timeout when trying to reach Microsoft Graph API")
            raise HTTPException(status_code=504, detail="Connection timeout when trying to reach Microsoft Graph API")
        except Exception as e:
            logging.error(f"Error making request to Microsoft Graph API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error making request to Microsoft Graph API: {str(e)}")

    if response.status_code == 201:
        logging.info("Notebook created successfully")
        return {"message": "Notebook created successfully", "data": response.json()}
    else:
        logging.error(f"Error creating notebook: {response.status_code} - {response.text}")
        raise HTTPException(status_code=response.status_code, detail=f"Error creating notebook: {response.text}")