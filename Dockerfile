FROM python:latest
WORKDIR /app/backend

COPY requirements.txt .

# Combine system dependencies installation and Python package installation
RUN apt-get update && apt-get install -y \
    libreoffice \
    poppler-utils \
    && python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

EXPOSE ${PORT_BACKEND}

# Ensure commands run inside the virtual environment
CMD ["/bin/bash", "-c", "source /opt/venv/bin/activate && python main.py"]