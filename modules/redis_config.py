from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_modules_redis_config'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from redis import Redis

REDIS_URL = os.getenv("LOCAL_REDIS_URL", "redis://localhost:6379")
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

def get_cached_results(cache_key):
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logging.info(f"Cached data: {cached_data}")
            return eval(cached_data)
        return None
    except Exception as e:
        print(f"Redis cache error: {e}")
        return None

def set_cached_results(cache_key, results):
    try:
        redis_client.setex(cache_key, CACHE_TTL, str(results))
        logging.info(f"Cached results: {results}")
    except Exception as e:
        print(f"Redis cache error: {e}")