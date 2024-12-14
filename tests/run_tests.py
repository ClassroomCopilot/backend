from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import os
import sys
import subprocess
from datetime import datetime
import webbrowser
import threading
import shutil
import time

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import modules.logger_tool as logger

# Setup logging
log_name = 'pytest_run_tests'
log_dir = os.getenv("LOG_PATH", "/logs")  # Default path as fallback
logging = logger.get_logger(
    name=log_name,
    log_level=os.getenv("LOG_LEVEL", "DEBUG"),
    log_path=log_dir,
    log_file=log_name,
    runtime=True,
    log_format='default'
)

def find_project_root():
    # Start from the current file location
    root = os.path.dirname(os.path.abspath(__file__))
    # Traverse up until you find the .env file
    while not os.path.exists(os.path.join(root, '.env')):
        new_root = os.path.dirname(root)
        if root == new_root:  # root directory reached without finding .env
            raise Exception("Project root not found.")
        root = new_root
    return root

def load_env():
    project_root = find_project_root()
    dotenv_path = find_dotenv(os.path.join(project_root, '.env'))
    load_dotenv(dotenv_path)
    required_vars = ["VITE_FASTAPI_HOST", "VITE_FASTAPI_PORT", "USERPROFILE", "APP_DIR", "EXCEL_CURRICULUM_FILE", "EXCEL_TIMETABLE_FILE"]
    for var in required_vars:
        if var not in os.environ:
            print(f"Error: {var} is not set in the environment.")
            sys.exit(1)

def select_test_file():
    project_root = find_project_root()
    test_categories = {
        "A": {
            "name": "X Copilot Initialization",
            "tests": {
                "1": os.path.join(project_root, "backend", "app", "tests", "pytest_init_x.py")
            }
        },
        "B": {
            "name": "Graph QA",
            "tests": {
                "1": os.path.join(project_root, "backend", "app", "tests", "pytest_init_school_timetable_graph_qa.py"),
                "2": os.path.join(project_root, "backend", "app", "tests", "pytest_init_curriculum_graph_qa.py"),
                "3": os.path.join(project_root, "backend", "app", "tests", "pytest_init_calendar_graph_qa.py")
            }
        },
        "C": {
            "name": "Connections",
            "tests": {
                "1": os.path.join(project_root, "backend", "app", "tests", "pytest_arbor.py")
            }
        },
        "D": {
            "name": "Transcription",
            "tests": {
                "1": os.path.join(project_root, "tests", "pytest_transcribe.py")
            }
        },
        "E": {
            "name": "LangGraph",
            "tests": {
                "1": os.path.join(project_root, "backend", "app", "tests", "pytest_langgraph.py")
            }
        }
    }

    print("Select a test file to run:")
    for category_key, category in test_categories.items():
        print(f"\n{category_key}: {category['name']}")
        for test_key, test_file in category["tests"].items():
            print(f"  {category_key}{test_key}: {os.path.basename(test_file)}")

    choice = input("\nEnter your choice (e.g., A1): ").upper()
    if len(choice) == 2 and choice[0] in test_categories and choice[1] in test_categories[choice[0]]["tests"]:
        category_key, test_key = choice[0], choice[1]
        return test_categories[category_key]["tests"][test_key], choice

    print("Invalid choice.")
    sys.exit(1)

def create_log_dir(choice, project_root):
    log_dir = os.path.join(project_root, "logs", "pytests")
    if choice[0] == "A":
        log_dir = os.path.join(log_dir, "database", "init")
    elif choice[0] == "B":
        log_dir = os.path.join(log_dir, "database", "langchain", "graph_qa")
    elif choice[0] == "C":
        log_dir = os.path.join(log_dir, "database", "connections", "arbor")
    elif choice[0] == "D":
        log_dir = os.path.join(log_dir, "transcribe")
    elif choice[0] == "E":
        log_dir = os.path.join(log_dir, "langgraph")
    else:
        print("Invalid choice.")
        sys.exit(1)
    
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def open_html_report_in_browser(html_path):
    """Function to open the HTML report in the default web browser."""
    # Check for the existence of the file every 2 seconds, up to a maximum of 10 checks
    for _ in range(10):
        if os.path.exists(html_path):
            webbrowser.open(html_path)
            break
        time.sleep(2)
    else:
        print("HTML report was not generated in time.")

def run_tests(test_file, log_dir, choice):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = os.path.basename(test_file).replace('.py', '')
    html_report = os.path.join(log_dir, f"{base_filename}_pytest_report_{timestamp}.html")
    xml_report = os.path.join(log_dir, f"{base_filename}_pytest_report_{timestamp}.xml")
    
    pytest_command = [
        "pytest",
        "-v",
        test_file,
        f"--junitxml={xml_report}",
        f"--html={html_report}",
        "--self-contained-html",
        "--capture=tee-sys",
        "--show-capture=all"
    ]

    if choice[0] == "A":
        test_components = input("Enter test components to run (school,users,timetable), comma-separated, or 'all': ").lower()
        if test_components != 'all':
            components = test_components.split(',')
            for component in components:
                pytest_command.append(f"-m {component}")

    print("Running command:", ' '.join(pytest_command))

    # Start a thread to open the HTML report, checking for its existence
    threading.Thread(target=open_html_report_in_browser, args=(html_report,)).start()

    result = subprocess.run(pytest_command, check=True)
    return result

def main():
    project_root = find_project_root()
    load_env()
    data_dir = os.path.join(project_root, "APP_DATA")
    # TODO: Modify this after initial testing
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    test_file, choice = select_test_file()
    if not test_file:
        print("Invalid choice.")
        sys.exit(1)

    log_dir = create_log_dir(choice, project_root)
    run_tests(test_file, log_dir, choice)

if __name__ == "__main__":
    main()
