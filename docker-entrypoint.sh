#!/bin/bash
set -e

# Add backend to Python path
export PYTHONPATH="/app/backend:${PYTHONPATH}"

# Create init directories
mkdir -p /init/data

# Function to check if initialization is needed
check_init_needed() {
    if [ ! -f "/init/status.json" ]; then
        return 0
    fi
    
    # Check if any status is incomplete
    incomplete=$(python -c "
import json
try:
    with open('/init/status.json', 'r') as f:
        status = json.load(f)
    print(not all(v for k, v in status.items() if k != 'timestamp'))
except (FileNotFoundError, json.JSONDecodeError):
    print('True')
")
    
    if [ "$incomplete" = "True" ]; then
        return 0
    else
        return 1
    fi
}

# Run initialization if needed
if check_init_needed; then
    echo "Running initialization..."
    python -c "from run.initialization import initialize_system; initialize_system()"
else
    echo "System already initialized, skipping..."
fi

# Execute the main command
exec "$@" 