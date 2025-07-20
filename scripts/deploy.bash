#!/bin/bash

set -e

echo "📦 Starting deployment..."
ls -la

# Pull latest changes
echo "🔄 Pulling latest code..."
git pull origin main

# Stop any running containers
echo "🛑 Stopping existing Docker containers..."
docker compose down

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating production environment file..."
    TIMESTAMP=$(date +%s)
    cat > .env << EOF
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_prod_password_${TIMESTAMP}
POSTGRES_DB=backtesting_db
DATABASE_URL=postgresql://postgres:secure_prod_password_${TIMESTAMP}@db:5432/backtesting_db
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["*"]
DEBUG=True
DATABASE_ECHO=False
# Redis Configuration
REDIS_URL=redis://redis:6379/0

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_secure_${TIMESTAMP}
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Build and start Docker services
echo "🚀 Building and starting Docker services..."
docker compose build
docker compose up -d

echo "🕒 Waiting for FastAPI to be ready..."
sleep 10  # Replace with a healthcheck or wait-for-it script if needed

# Run Alembic migrations
echo "⚙️ Running Alembic migrations..."
docker exec -it fastapi_app bash -c "cd backend && alembic upgrade head"
echo "✅ Migrations applied."

# Call API to populate companies
echo "📡 Calling API to populate companies..."
curl -X POST http://localhost:8000/api/v1/populate/populate/companies/
echo "✅ Company data populated."

# Build frontend
echo "🎨 Building frontend..."
cd frontend
pnpm install

echo "🚀 Starting frontend dev server..."
# Build static assets
pnpm run dev

echo "✅ Frontend built successfully!"

echo ""
echo "🎉 Local Deployment completed!"
echo "🔗 Backend: http://localhost:8000"
echo "🔗 pgAdmin: http://localhost:5050"
echo "🌐 Frontend http://localhost:3000"
