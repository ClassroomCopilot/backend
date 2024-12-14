from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_interactive_langgraph_query'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from modules.langchain.interactive_langgraph_query import perplexity_clone_graph
from modules.redis_config import get_cached_results, set_cached_results
from langchain_core.messages import HumanMessage

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    use_cache: bool = False

class QueryResponse(BaseModel):
    response: str
    needs_more_info: bool

@router.post("/query", response_model=QueryResponse)
async def interactive_query(request: QueryRequest):
    logging.info(f"Received query: {request.query}")
    try:
        query_id = generate_random_alphanumeric()
        config = {"configurable": {"thread_id": f'{query_id}'}, "recursion_limit": 20}
        
        inputs = {
            "messages": [HumanMessage(content=request.query)],
        }
        
        # Check cache for existing results only if VITE_DEV is false
        use_cache = os.getenv("VITE_DEV", "true").lower() == "false"
        if use_cache:
            cache_key = f"langgraph_query:{request.query}"
            cached_result = get_cached_results(cache_key)
            if cached_result:
                logging.info(f"Found cached result for query: {request.query}")
                return cached_result
        
        logging.debug("Updating state with initial message")
        perplexity_clone_graph.update_state(config, inputs)
        
        logging.debug("Invoking perplexity_clone_graph")
        outputs = await perplexity_clone_graph.ainvoke(inputs, config)
        
        final_response = outputs['messages'][-1].content
        needs_more_info = outputs.get('needs_more_info', False)
        
        logging.info(f"Final response: {final_response}")
        logging.info(f"Needs more info: {needs_more_info}")
        
        response = QueryResponse(response=final_response, needs_more_info=needs_more_info)
        
        # Cache the result only if VITE_DEV is false
        if use_cache:
            set_cached_results(cache_key, response.dict())
        
        return response
    except Exception as e:
        logging.error(f"Error in interactive query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during the query process: {str(e)}")

def generate_random_alphanumeric(length=4):
    import random
    import string
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))
