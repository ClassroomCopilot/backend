import os
import sys
import json
import requests

def format_timetable_with_ollama(timetable_data):
    url = f"http://{os.environ.get('HOST_BACKEND')}:{os.environ.get('PORT_BACKEND')}/llm/private/ollama/ollama_generate"
    headers = {"Content-Type": "application/json"}
    prompt = (
        "Create a markdown formatted table of the following timetable data. "
        "The table should have columns for 'Day', 'Time Slot', 'Effective Dates', 'Event', 'Room', and 'Staff':\n\n"
        f"{json.dumps(timetable_data, indent=4)}"
    )
    payload = {
        "model": "llama3",  # Adjust the model name if necessary
        "prompt": prompt
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("response")
    else:
        raise Exception(f"Failed to get response from Ollama: {response.status_code} {response.text}")

if __name__ == "__main__":
    input_data = sys.stdin.read()
    try:
        timetable_data = json.loads(input_data)
        markdown_table = format_timetable_with_ollama(timetable_data)
        print(markdown_table)
    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)