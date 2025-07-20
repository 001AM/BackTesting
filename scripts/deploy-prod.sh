#!/bin/bash

# deploy-prod.sh - Deployment script for code updates only
# This script updates Docker containers without creating new AWS resources

set -e  # Exit on any error

echo "🚀 Starting production deployment..."
echo "📦 Image: ${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHA}"

# Validate required environment variables
if [ -z "$CI_REGISTRY_IMAGE" ] || [ -z "$CI_COMMIT_SHA" ]; then
    echo "❌ Required environment variables not set!"
    echo "CI_REGISTRY_IMAGE: ${CI_REGISTRY_IMAGE:-NOT_SET}"
    echo "CI_COMMIT_SHA: ${CI_COMMIT_SHA:-NOT_SET}"
    exit 1
fi

# Check if this is the first deployment or an update
if [ -f "docker-compose.prod.yml" ] && [ -d "/home/ubuntu" ]; then
    echo "🔄 Updating existing deployment..."
    DEPLOYMENT_TYPE="UPDATE"
else
    echo "🆕 First-time deployment setup..."
    DEPLOYMENT_TYPE="INITIAL"
fi

# Login to GitLab Container Registry
echo "🔐 Logging into GitLab Container Registry..."
echo "${CI_REGISTRY_PASSWORD}" | docker login -u "${CI_REGISTRY_USER}" --password-stdin "${CI_REGISTRY_IMAGE%/*}"

# Create .env.prod file if it doesn't exist (only for initial deployment)
if [ ! -f ".env.prod" ]; then
    echo "📝 Creating production environment file..."
    TIMESTAMP=$(date +%s)
    cat > .env.prod << EOF
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_prod_password_${TIMESTAMP}
POSTGRES_DB=backtesting_db
DATABASE_URL=postgresql://postgres:secure_prod_password_${TIMESTAMP}@db:5432/backtesting_db
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["*"]
DEBUG=False
DATABASE_ECHO=False
# Redis Configuration
REDIS_URL=redis://redis:6379/0

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_secure_${TIMESTAMP}

# Application Configuration
CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE}
IMAGE_TAG=${CI_COMMIT_SHA}
EOF
    echo "✅ Environment file created"
else
    echo "📝 Updating image tag in existing .env.prod..."
    # Update both IMAGE_TAG and CI_REGISTRY_IMAGE to ensure consistency
    sed -i "s|IMAGE_TAG=.*|IMAGE_TAG=${CI_COMMIT_SHA}|" .env.prod
    sed -i "s|CI_REGISTRY_IMAGE=.*|CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE}|" .env.prod
    
    # Add CI_REGISTRY_IMAGE if it doesn't exist
    if ! grep -q "CI_REGISTRY_IMAGE=" .env.prod; then
        echo "CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE}" >> .env.prod
    fi
fi

# Export environment variables for docker-compose
export CI_REGISTRY_IMAGE="${CI_REGISTRY_IMAGE}"
export IMAGE_TAG="${CI_COMMIT_SHA}"

# Source the .env.prod file to make all variables available to docker-compose
if [ -f ".env.prod" ]; then
    echo "📋 Loading environment variables from .env.prod..."
    set -a  # automatically export all variables
    source .env.prod
    set +a  # stop automatically exporting
fi

echo "🔍 Environment variables check:"
echo "CI_REGISTRY_IMAGE: ${CI_REGISTRY_IMAGE}"
echo "IMAGE_TAG: ${IMAGE_TAG}"
echo "DATABASE_URL: ${DATABASE_URL}"
echo "REDIS_URL: ${REDIS_URL}"
echo "Full image reference: ${CI_REGISTRY_IMAGE}:${IMAGE_TAG}"

# Pull the latest image
echo "📥 Pulling latest Docker image..."
docker pull "${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHA}"

# Stop existing containers gracefully
if [ "$DEPLOYMENT_TYPE" = "UPDATE" ]; then
    echo "🛑 Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans || echo "⚠️  No existing containers to stop"
    
    # Clean up unused images to save disk space
    echo "🧹 Cleaning up old Docker images..."
    docker image prune -f --filter "until=24h" || true
    
    # Clean up unused networks
    echo "🧹 Cleaning up unused networks..."
    docker network prune -f || true
fi

# Debug: Show the actual docker-compose configuration
echo "🔍 Docker Compose configuration check:"
echo "Running: docker-compose -f docker-compose.prod.yml config"
if ! docker-compose -f docker-compose.prod.yml config; then
    echo "❌ Docker Compose configuration is invalid!"
    echo "📋 Current environment variables:"
    echo "CI_REGISTRY_IMAGE: ${CI_REGISTRY_IMAGE}"
    echo "IMAGE_TAG: ${IMAGE_TAG}"
    echo "DATABASE_URL: ${DATABASE_URL}"
    echo "REDIS_URL: ${REDIS_URL}"
    echo "📋 .env.prod content:"
    cat .env.prod || echo "❌ .env.prod not found"
    exit 1
fi

# Start the application
echo "🔄 Starting production containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for database to be healthy first
echo "⏳ Waiting for database to be healthy..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres -d backtesting_db > /dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi
    echo "⏳ Database health check attempt $i/30..."
    sleep 5
    if [ $i -eq 30 ]; then
        echo "❌ Database failed to become healthy!"
        echo "📋 Database logs:"
        docker-compose -f docker-compose.prod.yml logs db
        exit 1
    fi
done

# Wait for Redis to be healthy
echo "⏳ Waiting for Redis to be healthy..."
for i in {1..10}; do
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is ready!"
        break
    fi
    echo "⏳ Redis health check attempt $i/10..."
    sleep 3
    if [ $i -eq 10 ]; then
        echo "❌ Redis failed to become healthy!"
        echo "📋 Redis logs:"
        docker-compose -f docker-compose.prod.yml logs redis
        exit 1
    fi
done

# Test network connectivity from app container to database
echo "🔍 Testing network connectivity..."
sleep 10  # Give app container time to start

# Check if app container can resolve db hostname
if docker-compose -f docker-compose.prod.yml exec -T app nslookup db > /dev/null 2>&1; then
    echo "✅ App container can resolve 'db' hostname"
else
    echo "⚠️  App container cannot resolve 'db' hostname, checking network..."
    docker network ls
    docker-compose -f docker-compose.prod.yml exec -T app cat /etc/resolv.conf || true
fi

# Health checks
echo "🏥 Performing health checks..."

# Check if containers are running
echo "🔍 Checking container status..."
docker-compose -f docker-compose.prod.yml ps

if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "❌ Some containers failed to start!"
    echo "📋 Container logs:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# Check application health endpoint with extended retries
echo "🔍 Checking application health endpoint..."
for i in {1..20}; do
    if curl -f -m 10 http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Application is healthy!"
        break
    fi
    echo "⏳ Health check attempt $i/20..."
    
    # Show app logs on every 5th attempt
    if [ $((i % 5)) -eq 0 ]; then
        echo "📋 Recent app logs:"
        docker-compose -f docker-compose.prod.yml logs --tail=10 app
    fi
    
    sleep 15
    if [ $i -eq 20 ]; then
        echo "❌ Application health check failed!"
        echo "📋 Full application logs:"
        docker-compose -f docker-compose.prod.yml logs app
        echo "📋 Database logs:"
        docker-compose -f docker-compose.prod.yml logs db
        echo "📋 Network information:"
        docker network inspect $(docker-compose -f docker-compose.prod.yml ps -q app | head -1 | xargs docker inspect --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}') || true
        exit 1
    fi
done

# Run Alembic migrations inside the container
echo "🔄 Running Alembic migrations..."
if docker-compose -f docker-compose.prod.yml exec -T app bash -c "cd backend && alembic upgrade head"; then
    echo "✅ Migrations completed successfully."
else
    echo "⚠️  Migration failed, attempting to create tables manually..."
    docker-compose -f docker-compose.prod.yml logs app
fi

# If initial deployment, call the populate companies API
if [ "$DEPLOYMENT_TYPE" = "INITIAL" ]; then
    echo "📡 Initial deployment: calling /api/v1/populate/populate/companies/..."
    
    for i in {1..10}; do
        if curl -f -X POST -m 30 http://localhost:8000/api/v1/populate/populate/companies/; then
            echo "✅ API call succeeded!"
            break
        fi
        echo "⏳ Retrying API call ($i/10)..."
        sleep 15
        if [ $i -eq 10 ]; then
            echo "❌ Failed to call populate API after multiple attempts."
            echo "⚠️  Deployment completed but initial data population failed."
            echo "📋 You may need to manually call the populate API later."
        fi
    done
fi

# Show deployment summary
echo ""
echo "🎉 Deployment completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Deployment Summary:"
echo "   Type: $DEPLOYMENT_TYPE"
echo "   Image: ${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHA}"
echo "   Status: RUNNING"
echo ""
echo "🌐 Service URLs:"
echo "   Application: http://$(curl -s http://checkip.amazonaws.com):8000"
echo "   Health Check: http://$(curl -s http://checkip.amazonaws.com):8000/health"
echo "   pgAdmin: http://$(curl -s http://checkip.amazonaws.com):5050"
echo ""
echo "🐳 Container Status:"
docker-compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Optional: Show resource usage
echo "💾 System Resources:"
echo "   Memory: $(free -h | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "   Disk: $(df -h / | awk 'NR==2{printf "%s", $5}')"

# Show network information for debugging
echo "🌐 Network Information:"
echo "   App Network: $(docker network ls | grep app-network || echo 'Not found')"
echo "   Container IPs:"
docker-compose -f docker-compose.prod.yml exec -T app hostname -I 2>/dev/null || echo "   App: Could not determine IP"
docker-compose -f docker-compose.prod.yml exec -T db hostname -I 2>/dev/null || echo "   DB: Could not determine IP"

echo "✅ Production deployment completed successfully!"