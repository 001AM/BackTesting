#!/bin/bash
# Deploy script for FastAPI application

set -e

echo "Starting deployment..."

# Pull latest changes
git pull origin main

# Build and start services
docker-compose down
docker-compose build
docker-compose up -d

echo "Deployment completed successfully!"
echo "Application is running at http://localhost:8000"
echo "pgAdmin is available at http://localhost:5050"