import sys
import os
import json
import requests

def format_timetable_with_openai(timetable_data):
    url = f"http://{os.environ.get('VITE_FASTAPI_HOST')}:{os.environ.get('VITE_FASTAPI_PORT')}/llm/public/openai/openai_general_prompt"
    headers = {"Content-Type": "application/json"}
    prompt = (
        "Create a markdown formatted table of the following timetable data. "
        "The table should have columns for 'Day', 'Time Slot', 'Effective Dates', 'Event', 'Room', and 'Staff':\n\n"
        f"{json.dumps(timetable_data, indent=4)}"
    )
    payload = {
        "model": "gpt-4-turbo",  # Adjust the model name if necessary
        "prompt": prompt,
        "max_tokens": 1500,
        "temperature": 0.7,
        "top_p": 1.0,
        "n": 1,
        "stop": None
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("response")
    else:
        raise Exception(f"Failed to get response from OpenAI: {response.status_code} {response.text}")

if __name__ == "__main__":
    input_data = sys.stdin.read()
    try:
        timetable_data = json.loads(input_data)
        markdown_table = format_timetable_with_openai(timetable_data)
        
        # Save the markdown table to a .md file
        output_file = "timetable.md"
        with open(output_file, "w") as file:
            file.write(markdown_table)
        
        print(f"Markdown table saved to {output_file}")
    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)