# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /backend

# Install system dependencies (including Chrome and driver dependencies)
RUN apt-get update && apt-get install -y \
    gcc wget unzip curl gnupg ca-certificates fonts-liberation \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 \
    libappindicator3-1 libasound2 xdg-utils libgtk-3-0 \
    chromium chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables to point to Chrome
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER_PATH="/usr/lib/chromium/chromedriver"

# Copy requirements file
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
COPY backend/ backend/

# Expose FastAPI port
EXPOSE 8000

# Default command to run the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
