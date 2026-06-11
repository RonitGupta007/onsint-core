# Use an official lightweight Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to optimize Python runtime in container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/ig_int_vault.db

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create persistent data directory for SQLite database
RUN mkdir -p /app/data

# Expose port for the FastAPI server
EXPOSE 8000

# Start Uvicorn production server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
