# 🚀 Deployment Guide - Full Stack Equity Backtesting Platform

This guide covers both **local development** and **production deployment** on AWS using GitLab CI/CD.

## 📋 Table of Contents

- [Local Development](#-local-development)
- [Production Deployment](#-production-deployment-aws--gitlab-cicd)
- [Environment Variables](#-environment-variables)
- [Security Best Practices](#-security-best-practices)
- [Troubleshooting](#-troubleshooting)
- [Monitoring](#-monitoring)

---

## 🔐 Security Best Practices

### GitLab CI/CD Variable Security

1. **Variable Protection Levels**:
   - ✅ **Protected**: Variables only available on protected branches
   - ✅ **Masked**: Variable values hidden in job logs
   - ✅ **Expanded**: Variables expanded in runtime (required for complex values)

2. **SSH Key Management**:
   ```bash
   # Generate SSH key pair for EC2 access
   ssh-keygen -t rsa -b 4096 -C "gitlab-ci@yourdomain.com" -f gitlab-ci-key
   
   # Add public key to EC2 instance
   # Add private key to GitLab CI/CD variables as SSH_PRIVATE_KEY
   ```

3. **AWS Credentials Security**:
   - Create IAM user with minimal required permissions
   - Enable MFA on AWS account
   - Rotate access keys regularly
   - Use AWS IAM roles where possible

4. **Database Security**:
   - Use strong passwords (generated with timestamp in deploy script)
   - Limit database access to application containers only
   - Regular security updates for PostgreSQL

5. **Container Registry Security**:
   - Use GitLab's built-in container registry
   - Scan images for vulnerabilities
   - Use specific image tags instead of `latest`

### Production Environment Security

1. **Network Security**:
   ```bash
   # Configure AWS Security Groups
   # Allow only necessary ports:
   # - 22 (SSH) - Restrict to your IP
   # - 80 (HTTP) - Public
   # - 443 (HTTPS) - Public  
   # - 8000 (API) - Public or restricted
   # - 5432 (PostgreSQL) - Internal only
   ```

2. **SSL/TLS Configuration** (Recommended):
   ```yaml
   # Add to docker-compose.prod.yml
   nginx:
     image: nginx:alpine
     ports:
       - "80:80"
       - "443:443"
     volumes:
       - ./nginx.conf:/etc/nginx/nginx.conf
       - ./ssl:/etc/nginx/ssl
   ```

3. **Environment Variables**:
   - Never commit `.env` files to version control
   - Use different passwords for different environments
   - Implement secrets rotation

4. **Monitoring & Logging**:
   ```bash
   # Enable AWS CloudWatch (optional)
   # Set up log aggregation
   # Monitor failed login attempts
   # Set up alerting for security events
   ```

---

## 🏠 Local Development

### Prerequisites

- Docker & Docker Compose
- Node.js (v18+) & pnpm
- Git

### Quick Start

1. **Clone Repository**
   ```bash
   git clone https://github.com/001AM/BackTesting.git
   cd BackTesting
   ```

2. **Run Automated Deployment**
   ```bash
   chmod +x deploy.bash
   ./deploy.bash
   ```

   This script will:
   - Pull latest code changes
   - Create environment files (`.env` and `backend/.env`)
   - Stop existing containers
   - Build and start Docker services
   - Run Alembic migrations
   - Populate company data
   - Start frontend development server

### Manual Local Setup

#### Backend Setup

1. **Start Database Services**
   ```bash
   docker compose up -d db pgadmin redis
   ```

2. **Create Backend Environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

4. **Start FastAPI Server**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Populate Initial Data**
   ```bash
   curl -X POST http://localhost:8000/api/v1/populate/populate/companies/
   ```

#### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   pnpm install
   ```

2. **Create Frontend Environment** (Optional for local)
   ```bash
   # frontend/.env
   VITE_API_URL=http://localhost:8000/api/v1
   ```

3. **Start Development Server**
   ```bash
   pnpm dev
   ```

### 🌐 Local URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | - |
| Frontend | http://localhost:3000 | - |
| pgAdmin | http://localhost:5050 | admin@example.com / adminpassword |
| API Docs | http://localhost:8000/docs | - |

---

## ☁️ Production Deployment (AWS + GitLab CI/CD)

### Prerequisites

- GitLab repository with CI/CD enabled
- AWS Account with EC2 access
- Terraform installed (for infrastructure)
- SSH key pair for EC2 access

### Infrastructure Setup (Terraform)

1. **Configure AWS Credentials**
   ```bash
   aws configure
   # or set environment variables:
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   ```

2. **Configure GitLab CI/CD Variables**
   
   Go to GitLab Project → Settings → CI/CD → Variables and add the following variables with **Protected**, **Masked**, and **Expanded** flags enabled:
   
   | Variable | Value | Description | Flags |
   |----------|-------|-------------|--------|
   | `AWS_ACCESS_KEY_ID` | `AKIA...` | AWS Access Key ID | Protected, Masked, Expanded |
   | `AWS_SECRET_ACCESS_KEY` | `xyz123...` | AWS Secret Access Key | Protected, Masked, Expanded |
   | `CI_REGISTRY` | `registry.gitlab.com` | GitLab Container Registry URL | Protected, Masked, Expanded |
   | `CI_REGISTRY_IMAGE` | `registry.gitlab.com/username/repo` | Full registry image path | Protected, Masked, Expanded |
   | `DATABASE_URL` | `postgresql://user:pass@host:port/db` | Production database URL | Protected, Masked, Expanded |
   | `EC2_KEY_NAME` | `your-key-pair-name` | AWS EC2 Key Pair name | Protected, Expanded |
   | `SSH_PRIVATE_KEY` | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Private key for EC2 access | Protected, Expanded |

   ### Variable Security Settings:
   - **Protected**: Only available on protected branches (main/master)
   - **Masked**: Values hidden in job logs
   - **Expanded**: Variables expanded in runtime environment

### Deployment Pipeline

The GitLab CI/CD pipeline automatically:

1. **Terraform Plan** - Checks infrastructure changes
2. **Terraform Apply** - Creates/updates AWS resources
3. **Build Image** - Creates Docker image
4. **Deploy** - Updates application on EC2

### Pipeline Stages

```yaml
stages:
  - terraform-plan    # Plan infrastructure changes
  - terraform-apply   # Apply infrastructure
  - build            # Build Docker images
  - deploy           # Deploy to EC2
```

### Manual Production Deployment

If you need to deploy manually:

1. **SSH into EC2 Instance**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

2. **Pull Latest Code**
   ```bash
   git pull origin main
   ```

3. **Run Production Deployment**
   ```bash
   chmod +x scripts/deploy-prod.sh
   ./scripts/deploy-prod.sh
   ```

### Production URLs

After successful deployment:

| Service | URL | Notes |
|---------|-----|-------|
| Application | `http://YOUR_EC2_IP:8000` | Main API |
| Health Check | `http://YOUR_EC2_IP:8000/health` | Health endpoint |
| pgAdmin | `http://YOUR_EC2_IP:5050` | Database admin |

---

## 🔧 Environment Variables

### Local Development (.env)

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=backtesting_db
DATABASE_URL=postgresql://postgres:password@db:5432/backtesting_db

# API Configuration
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["*"]
DEBUG=True
DATABASE_ECHO=False

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=adminpassword
```

### Production (.env.prod)

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_prod_password_TIMESTAMP
POSTGRES_DB=backtesting_db
DATABASE_URL=postgresql://postgres:secure_prod_password_TIMESTAMP@db:5432/backtesting_db

# API Configuration
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["https://yourdomain.com"]
DEBUG=False
DATABASE_ECHO=False

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_secure_TIMESTAMP

# Docker Configuration
CI_REGISTRY_IMAGE=registry.gitlab.com/your-username/backtesting
IMAGE_TAG=latest
```

### Frontend Environment

```env
# For local development
VITE_API_URL=http://localhost:8000/api/v1

# For production (if using separate frontend deployment)
VITE_API_URL=http://YOUR_EC2_IP:8000/api/v1
```

---

## 🛠 Troubleshooting

### Local Development Issues

#### Docker Issues
```bash
# Reset Docker environment
docker compose down -v
docker system prune -a
docker compose up --build
```

#### Database Connection Issues
```bash
# Check if database is running
docker compose ps
docker compose logs db

# Reset database
docker compose down -v
docker compose up -d db
```

#### Port Conflicts
```bash
# Check what's using port 8000
lsof -i :8000
# Kill the process if needed
kill -9 PID
```

### Production Issues

#### SSH Connection Problems
```bash
# Test SSH connection
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Check security groups - ensure ports are open:
# - 22 (SSH)
# - 8000 (API)
# - 5050 (pgAdmin)
```

#### Application Not Starting
```bash
# SSH into EC2 and check logs
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
docker compose -f docker-compose.prod.yml logs app
docker compose -f docker-compose.prod.yml ps
```

#### Database Issues
```bash
# Check database health
docker compose -f docker-compose.prod.yml exec db pg_isready -U postgres -d backtesting_db

# View database logs
docker compose -f docker-compose.prod.yml logs db
```

#### Image Pull Issues
```bash
# Manual login to GitLab registry
docker login registry.gitlab.com
docker pull registry.gitlab.com/your-username/backtesting:latest
```

---

## 📊 Monitoring

### Health Checks

- **Application Health**: `GET /health`
- **Database Health**: Built-in Docker health checks
- **Redis Health**: Built-in Docker health checks

### Log Monitoring

#### Local Logs
```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f app
docker compose logs -f db
```

#### Production Logs
```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# View production logs
docker compose -f docker-compose.prod.yml logs -f app
docker compose -f docker-compose.prod.yml logs -f db
```

### Resource Monitoring

#### Local Resource Usage
```bash
# Docker stats
docker stats

# System resources
top
df -h
free -h
```

#### Production Resource Usage
```bash
# SSH into EC2 and check resources
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
htop
df -h
free -h
docker stats
```

### Performance Monitoring

- Monitor API response times via `/health` endpoint
- Check database query performance in logs
- Monitor Docker container resource usage
- Set up CloudWatch monitoring for EC2 (optional)

---

## 🔄 Deployment Workflow

### Development Workflow
1. Make code changes locally
2. Test using `docker compose up`
3. Commit and push to GitLab
4. Pipeline automatically deploys to production

### Production Rollback
```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Pull previous image version
docker pull registry.gitlab.com/your-username/backtesting:PREVIOUS_SHA

# Update .env.prod with previous image tag
sed -i "s|IMAGE_TAG=.*|IMAGE_TAG=PREVIOUS_SHA|" .env.prod

# Restart containers
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Pipeline Debugging

Check GitLab CI/CD pipeline logs:
1. Go to GitLab → CI/CD → Pipelines
2. Click on failed pipeline
3. Review stage-specific logs
4. Common issues:
   - Terraform state conflicts
   - Docker build failures
   - SSH connectivity issues
   - Environment variable misconfigurations

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review pipeline logs in GitLab
3. Check application logs via Docker
4. Verify environment variables
5. Ensure all prerequisites are met
