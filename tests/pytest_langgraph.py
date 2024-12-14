from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_interactive_langgraph_query'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
import pytest
import requests

# Define the URL of your FastAPI server
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/langchain/interactive_langgraph_query/query"

def send_query(query):
    payload = {"query": query}
    headers = {"Content-Type": "application/json"}
    logging.info(f"Sending query to {ENDPOINT} with payload: {payload}")
    
    try:
        response = requests.post(ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        logging.info(f"Received response from {ENDPOINT}: {result}")
        return result
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending query to {ENDPOINT}: {str(e)}")
        return {"error": str(e)}

@pytest.mark.simple
def test_simple_queries():
    query = "Describe the relevance of Maidstone, England during the English Civil War."
    logging.info(f"Running simple query test with query: {query}")
    result = send_query(query)
    
    logging.info(f"Assertion 1: Checking for absence of error")
    assert "error" not in result, f"Error in response: {result.get('error')}"
    
    logging.info(f"Assertion 2: Checking for presence of response")
    assert "response" in result, "Response does not contain an answer"
    
    logging.info(f"Assertion 3: Checking for non-empty answer")
    assert len(result["response"]) > 0, "Answer is empty"
    
    logging.info(f"All assertions passed. Response: {result['response'][:100]}...")

@pytest.mark.followup
def test_followup_queries():
    initial_query = "What is the latest local news from a particular town?"
    logging.info(f"Running followup query test with initial query: {initial_query}")
    result = send_query(initial_query)
    
    logging.info(f"Assertion 1: Checking for absence of error")
    assert "error" not in result, f"Error in response: {result.get('error')}"
    
    if result.get("needs_more_info", False):
        logging.info("Follow-up required. Sending follow-up query.")
        follow_up_query = f"{initial_query} The town is Maidstone."
        follow_up_result = send_query(follow_up_query)
        
        logging.info(f"Assertion 2: Checking for absence of error in follow-up")
        assert "error" not in follow_up_result, f"Error in follow-up response: {follow_up_result.get('error')}"
        
        logging.info(f"Assertion 3: Checking for presence of response in follow-up")
        assert "response" in follow_up_result, "Follow-up response does not contain an answer"
        
        logging.info(f"Assertion 4: Checking for non-empty answer in follow-up")
        assert len(follow_up_result["response"]) > 0, "Follow-up answer is empty"
        
        logging.info(f"All follow-up assertions passed. Response: {follow_up_result['response'][:100]}...")
    else:
        logging.info(f"Assertion 2: Checking for presence of response")
        assert "response" in result, "Response does not contain an answer"
        
        logging.info(f"Assertion 3: Checking for non-empty answer")
        assert len(result["response"]) > 0, "Answer is empty"
        
        logging.info(f"All assertions passed. Response: {result['response'][:100]}...")