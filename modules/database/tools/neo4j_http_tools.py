from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_database_tools_neo4j_http_tools'
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
import base64

vite_dev = os.getenv('VITE_DEV', 'false')

def send_query(query, encoded_credentials=None, params=None, method='POST', database="system", endpoint="/tx/commit"):
    if encoded_credentials is None:
        logging.debug(f"Sending query to Neo4j: {query}")
        credentials = f"{os.getenv('NEO4J_USER')}:{os.getenv('NEO4J_PASSWORD')}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode('utf-8')
        logging.debug(f"Encoded credentials: {encoded_credentials}")
    
    # Use HTTPS for production, HTTP for development
    protocol = 'http' if vite_dev else 'https' # TODO: Is SSL required for the Neo4j database?
    neo4j_url = f"{os.getenv('HOST_NEO4J')}:{os.getenv('PORT_NEO4J_HTTP')}" if vite_dev else f"{os.getenv('VITE_PUBLIC_NEO4J')}"
    url = f"{protocol}://{neo4j_url}/db/{database}{endpoint}"
    logging.debug(f"URL: {url}")
    headers = {'Content-Type': 'application/json', 'Authorization': f'Basic {encoded_credentials}'}
    logging.debug(f"Headers: {headers}")
    data = {
        "statements": [{
            "statement": query,
            "parameters": params or {}
        }]
    }
    logging.debug(f"Data: {data}")
    
    try:
        logging.debug(f"Sending request to Neo4j...")
        response = requests.request(method, url, json=data, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response content: {response.content}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Neo4j failed: {e}")
        raise

def create_node(node_type: str, node_data: dict, db=None):
    query = f"CREATE (n:{node_type} $props) RETURN id(n)"
    params = {"props": node_data}
    response = send_query(query, database=db, params=params)
    return response['results'][0]['data'][0]['meta'][0]['id']

def create_relationship(relationship_data: dict, db=None):
    query = """
    MATCH (a), (b) WHERE id(a) = $start_id AND id(b) = $end_id
    CREATE (a)-[r:{rel_type}]->(b)
    RETURN r
    """
    params = {"start_id": relationship_data['start_node']['id'], "end_id": relationship_data['end_node']['id'], "rel_type": relationship_data['relationship_type'], "props": relationship_data.get('properties', {})}
    return send_query("/db/neo4j/tx/commit", query, params, db=db)