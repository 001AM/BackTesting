#!/bin/bash
# Deploy script for FastAPI application

set -e

ls -la
echo "Starting deployment..."

# Pull latest changes
git pull origin main

# Build and start services
docker compose down
docker compose build
docker compose up -d
echo "Deployment completed successfully!"
echo "Application is running at http://localhost:8000"
echo "pgAdmin is available at http://localhost:5050"

# Wait for the FastAPI server to be ready (optional, adjust sleep time if needed)
echo "Waiting for the API to be ready..."
sleep 10  # or use healthcheck/wait-for-it script if needed

# Run Alembic migrations inside the container
echo "Running Alembic migrations..."
docker exec -it fastapi_app bash -c "cd backend && alembic upgrade head"
echo "Migrations completed."

# # Call the API endpoint
echo "Calling populate companies API..."
curl -X POST http://localhost:8000/api/v1/populate/populate/companies/

echo "API call completed."
