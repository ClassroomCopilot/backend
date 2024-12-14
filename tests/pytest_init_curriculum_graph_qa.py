import os
import json
import requests
import pytest
from dotenv import load_dotenv, find_dotenv
from .formatting import ascii_header
import modules.logger_tool as logger

load_dotenv(find_dotenv())

log_name = 'api_router_graph_qa_test'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

@pytest.fixture(scope="module")
def config():
    return {
        "database": "cc.ccschools.kevlarai",
        "top_k": 40,
        "model": "gpt-4o",
        "temperature": 0,
        "verbose": False,
        "return_intermediate_steps": True,
        "return_direct": False,
        "validate_cypher": True,
        "model_type": "openai"  # Default model_type
    }

def load_test_cases():
    with open('backend/app/tests/test_inputs/init_curriculum_db_cases.json', 'r') as f:
        return json.load(f)

test_cases = load_test_cases()

@pytest.mark.parametrize("case", test_cases["curriculum_cases"])
def test_curriculum_cases(case, config):
    assert run_test_case(case, config)

@pytest.mark.parametrize("case", test_cases["include_exclude_cases"]["includes"])
def test_include_cases(case, config):
    assert run_test_case(case, config)

@pytest.mark.parametrize("case", test_cases["include_exclude_cases"]["excludes"])
def test_exclude_cases(case, config):
    assert run_test_case(case, config)

@pytest.mark.parametrize("case", test_cases["include_exclude_cases"]["includes_excludes"])
def test_include_exclude_cases(case, config):
    assert run_test_case(case, config)

def run_test_case(case, config):
    logging.info(f"Starting test case with prompt: {case['prompt']}")
    url = f"http://{os.environ['VITE_FASTAPI_HOST']}:{os.environ['VITE_FASTAPI_PORT']}/api/langchain/graph_qa/prompt"
    params = {
        "database": config["database"],
        "prompt": case["prompt"],
        "top_k": config["top_k"],
        "model": config["model"],
        "temperature": config["temperature"],
        "verbose": config["verbose"],
        "return_intermediate_steps": config["return_intermediate_steps"],
        "exclude_types": case["exclude_types"],
        "include_types": case["include_types"],
        "return_direct": config["return_direct"],
        "validate_cypher": config["validate_cypher"],
        "model_type": config["model_type"]
    }
    logging.info(f"Constructed URL: {url}")
    logging.info(f"Parameters: {params}")

    try:
        logging.info("Sending request to API...")
        response = requests.get(url, params=params)
        logging.info(f"HTTP Response Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        logging.info(f"Response Data: {data}")

        # Log detailed test execution information
        logging.info("==================================================")
        logging.info("=                Test Execution                  =")
        logging.info("==================================================")
        logging.info(f"= Prompt: {data.get('query', 'N/A')}")
        logging.info("=                                                =")
        logging.info(f"= Query: \n{data.get('intermediate_steps', [{'query': 'N/A'}])[0].get('query', 'N/A')}")
        logging.info("=                                                =")
        logging.info("==================================================")

        # Determine if the test passed or failed
        response_text = data.get('result', 'N/A')
        context = data.get('intermediate_steps', [{'context': 'N/A'}])[1].get('context', 'N/A')
        if "I don't know" in response_text or not context:
            logging.error("==================================================")
            logging.error("=                  XX Test Failed XX             =")
            logging.error("==================================================")
            logging.error(f"= Prompt: {case['prompt']}")
            logging.error(f"= Context: {context}")
            logging.error(f"= Response: {response_text}")
            logging.error("==================================================")
            return False
        else:
            logging.info("==================================================")
            logging.info("=                  ** Test Passed **             =")
            logging.info("==================================================")
            logging.info(f"= Prompt: {case['prompt']}")
            logging.info(f"= Context: {context}")
            logging.info(f"= Response: {response_text}")
            logging.info("==================================================")
            return True
    except requests.exceptions.RequestException as e:
        logging.error("==================================================")
        logging.error("=                  ERROR                         =")
        logging.error("==================================================")
        logging.error(f"Error: {e}")
        logging.error("==================================================")
        return False