# Use a specific version of Python for better reproducibility
FROM python:3.9-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV AM_I_IN_A_DOCKER_CONTAINER=True

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY *.py .

# Create necessary directories
RUN mkdir -p /app/data
RUN mkdir -p /app/data/logs
RUN mkdir -p /app/config
RUN mkdir -p /app/pkls
RUN mkdir -p /app/lists

# Copy pkls
COPY pkls/*.pkl /app/pkls/

# Copy lists
COPY lists/*.txt /app/lists/

# Create a non-root user and switch to it
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run the application with Gunicorn
CMD ["python", "main.py"]