from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_langchain_graph_qa'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

def test_query_graph(database, prompt, top_k=20, model="gpt-4o", temperature=0, verbose=False, return_intermediate_steps=True, exclude_types=None, include_types=None, return_direct=False, validate_cypher=False, model_type="openai"):
    url = f"http://{os.environ['VITE_FASTAPI_HOST']}:{os.environ['VITE_FASTAPI_PORT']}/langchain/graph_qa/prompt"
    params = {
        "database": database,
        "prompt": prompt,
        "top_k": top_k,
        "model": model,
        "temperature": temperature,
        "verbose": verbose,
        "return_intermediate_steps": return_intermediate_steps,
        "exclude_types": exclude_types or [],
        "include_types": include_types or [],
        "return_direct": return_direct,
        "validate_cypher": validate_cypher,
        "model_type": model_type
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        logging.info("==================================================")
        logging.info("=                                                =")
        logging.info("=                Test Execution                  =")
        logging.info("=                                                =")
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
            return False, context, response_text
        else:
            return True, context, response_text
    except requests.exceptions.RequestException as e:
        logging.error("==================================================")
        logging.error("=                  ERROR                         =")
        logging.error("==================================================")
        logging.error(f"Error: {e}")
        logging.error("==================================================")
        return False, None, None