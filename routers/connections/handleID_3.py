import sys
import json

def filter_by_staff(data, staff_name="Kevin Carter"):
    return [entry for entry in data if entry.get("Staff") == staff_name]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        staff_name = sys.argv[1]
    else:
        staff_name = "Kevin Carter"
    
    input_data = sys.stdin.read()
    try:
        data = json.loads(input_data)
        filtered_data = filter_by_staff(data, staff_name)
        print(json.dumps(filtered_data, indent=4))
    except json.JSONDecodeError:
        print("Invalid JSON input", file=sys.stderr)