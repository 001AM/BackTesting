# 📊 Full Stack Equity Backtesting Platform

A production-ready backtesting platform for **Indian equities**, enabling users to define custom strategies, run historical backtests, and visualize key performance metrics — all with a modern UI and scalable backend.

---

## ✨ Features

- 🔍 **Custom Filters**: Market Cap, ROCE, PAT, etc.
- 🧠 **Smart Ranking**: Composite ranks using ROE, PE, and more
- ♻️ **Rebalancing**: Quarterly / Yearly
- ⚖️ **Position Sizing**: Equal, Market Cap, or Metric-based
- 📉 **Visual Insights**: Equity curve, drawdowns, win/loss charts
- 📤 **Exports**: Download metrics and logs as CSV/Excel
- 🧯 **Robust Logic**: No lookahead bias / future leakage

---

## 🧱 Project Structure

```
.
├── backend/            # FastAPI backend
│   └── config/         # Models, DB, services, utilities
├── frontend/           # React + Tailwind + ShadCN
│   └── src/            # Components, pages, hooks, etc.
├── scripts/            # CLI tools and automation scripts
├── Dockerfile          # Backend Docker configuration
├── docker-compose.yml  # Local dev environment
├── deploy.bash         # Auto-deploy script (local)
├── main.tf             # Terraform config (AWS EC2)
```

---

## 🚀 Quickstart (Docker)

```bash
git clone https://github.com/001AM/BackTesting.git
cd BackTesting
```

### 🔧 Frontend `.env` (If you want to use hosted aws backend only then create this .env in frontend folder)
```bash
cd frontend
```

```env
VITE_API_URL=http://3.95.224.95:8000/api/v1
```

### 🏗 Deploy

```bash
cd scripts
chmod +x deploy.bash
./deploy.bash
```

> This script:
> - Pulls latest code
> - Rebuilds Docker containers
> - Runs Alembic migrations
> - Populates company data via API
> - Starts frontend using `pnpm dev`

---

## 🌐 Local URLs

| Service     | URL                        |
|-------------|----------------------------|
| Backend API | http://localhost:8000      |
| Frontend UI | http://localhost:5173      |
| pgAdmin     | http://localhost:5050      |

---

## 🧪 Manual Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate     # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### Backend `.env`

```env
# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# API
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000"]
DEBUG=True

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=backtesting_db
DATABASE_URL=postgresql://postgres:password@localhost:5432/backtesting_db
DATABASE_ASYNC_URL=postgresql+asyncpg://postgres:password@localhost:5432/backtesting_db

# Redis
REDIS_URL=redis://redis:6379/0

# pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_secure
```

### Run Backend

```bash
docker compose up -d db
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Populate Companies

```bash
curl -X POST http://localhost:8000/api/v1/populate/populate/companies/
```

---

## 💻 Frontend Setup (Manual)

```bash
cd frontend
pnpm install
```

### Frontend `.env`

```env
#If you want to use hosted aws backend only then create this .env in frontend folder
VITE_API_URL=http://3.95.224.95:8000/api/v1
```

```bash
pnpm dev
```
---

## 🧠 Tech Stack

| Layer       | Tools                                   |
|-------------|------------------------------------------|
| Backend     | FastAPI, SQLAlchemy, Alembic, Pandas,Numpy     |
| Frontend    | React.js, Tailwind CSS, ShadCN           |
| Database    | PostgreSQL                               |
| Deployment  | Docker, Terraform (optional via EC2)     |
| Data Source | Yahoo Finance, Screener.in, NSE               |

---

## 🙋 Author

Built by **Soham Panchal**,  
Crafted to simplify backtesting of Indian stock market strategies.