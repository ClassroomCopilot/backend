FROM python:latest
WORKDIR /app

COPY requirements.txt .

# Combine system dependencies installation and Python package installation
RUN apt-get update && apt-get install -y \
    && python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

EXPOSE ${VITE_FASTAPI_PORT}

# Ensure commands run inside the virtual environment
CMD ["/bin/bash", "-c", "source /opt/venv/bin/activate && python main.py"]