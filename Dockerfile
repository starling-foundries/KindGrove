FROM python:3.10-slim

LABEL maintainer="Cameron Sajedi <cameron@starlingfoundries.com>"
LABEL description="Mangrove Biomass Estimation Workflow"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy workflow script
COPY mangrove_workflow_cli.py .

# Make script executable
RUN chmod +x mangrove_workflow_cli.py

# Default command shows help
CMD ["--help"]
