from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import modules.logger_tool as logger
log_name = 'api_routers_test_timetable'
user_profile = os.environ.get("USERPROFILE", "")
app_dir = os.environ.get("APP_DIR", "")
log_dir = os.path.join(user_profile, app_dir, "logs", "py_logger")
log_level = 'DEBUG'
logging = logger.get_logger(
    name=log_name,
    log_level=log_level,
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)
from fastapi import APIRouter

router = APIRouter()

@router.post("/run-pytest-timetable")
async def run_pytest_timetable():
    import subprocess    
    
    home_dir = os.environ['HOME_DIR']
    backend_test_dir = os.environ['BACKEND_TEST_DIR']
    logging.debug(f"original home_dir: {home_dir}")
    logging.debug(f"original backend_test_dir: {backend_test_dir}")
    
    if backend_test_dir[0] != '/':
        backend_test_dir = '/' + backend_test_dir
    
    # Convert backslashes to forward slashes for Windows compatibility
    home_dir = home_dir.replace('\\', '/')
    backend_test_dir = backend_test_dir.replace('\\', '/')
    logging.debug(f"new home_dir: {home_dir}")
    logging.debug(f"new backend_test_dir: {backend_test_dir}")
    
    # Join and normalize the path
    pytest_dir = os.path.normpath(os.path.join(home_dir, backend_test_dir.lstrip('/'), "pytest_timetable.py"))
    pytest_dir = pytest_dir.replace('\\', '/')  # Ensure forward slashes
    f_string = f"pytest {pytest_dir} --maxfail=1 --disable-warnings -q"
    logging.debug(f"f_string: {f_string}")
    
    result = subprocess.run(f_string, capture_output=True, text=True, shell=True)
    logging.debug(f"result: {result}")
    
    return {"stdout": result.stdout, "stderr": result.stderr}