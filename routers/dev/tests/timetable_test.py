from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)
from fastapi import APIRouter

router = APIRouter()

@router.post("/run-pytest-timetable")
async def run_pytest_timetable():
    import subprocess    
    
    home_dir = os.environ['HOME_DIR']
    backend_test_dir = os.environ['BACKEND_TEST_DIR']
    logger.debug(f"original home_dir: {home_dir}")
    logger.debug(f"original backend_test_dir: {backend_test_dir}")
    
    if backend_test_dir[0] != '/':
        backend_test_dir = '/' + backend_test_dir
    
    # Convert backslashes to forward slashes for Windows compatibility
    home_dir = home_dir.replace('\\', '/')
    backend_test_dir = backend_test_dir.replace('\\', '/')
    logger.debug(f"new home_dir: {home_dir}")
    logger.debug(f"new backend_test_dir: {backend_test_dir}")
    
    # Join and normalize the path
    pytest_dir = os.path.normpath(os.path.join(home_dir, backend_test_dir.lstrip('/'), "pytest_timetable.py"))
    pytest_dir = pytest_dir.replace('\\', '/')  # Ensure forward slashes
    f_string = f"pytest {pytest_dir} --maxfail=1 --disable-warnings -q"
    logger.debug(f"f_string: {f_string}")
    
    result = subprocess.run(f_string, capture_output=True, text=True, shell=True)
    logger.debug(f"result: {result}")
    
    return {"stdout": result.stdout, "stderr": result.stderr}