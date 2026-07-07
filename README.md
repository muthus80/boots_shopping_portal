# Boots Shopping App

A full-stack e-commerce application for boots and footwear, built with FastAPI (backend) and React (frontend), backed by PostgreSQL.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Environment Variables](#environment-variables)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Running Locally (without Docker)](#running-locally-without-docker)
- [Backend Structure](#backend-structure)
- [Frontend Structure](#frontend-structure)
- [API Domains](#api-domains)
- [Database Migrations](#database-migrations)
- [Testing](#testing)
- [Health Check](#health-check)

---

## Overview

Boots Shopping App is a modular monolith e-commerce platform that allows users to browse boots and footwear, manage a shopping cart, and complete purchases through a checkout flow. It features JWT-based authentication, a category-driven product catalog, and a clean separation of concerns across six business domains.

---

## Architecture

The application follows a **modular monolith** pattern:

- Each business domain (`account`, `auth`, `cart`, `categories`, `checkout`, `products`) lives in its own module under `app/domains/`.
- Modules communicate through well-defined service interfaces rather than direct cross-module database queries.
- The React frontend communicates with the backend exclusively through the versioned REST API (`/api/v1/`).
- PostgreSQL is the primary data store, accessed via async SQLAlchemy with Alembic for migrations.
- Authentication uses short-lived JWT access tokens and long-lived refresh tokens (with JTI for revocation support).

```
boots-shopping-app/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database, security utilities
│   │   ├── domains/
│   │   │   ├── account/    # User profile management
│   │   │   ├── auth/       # Login, register, token refresh
│   │   │   ├── cart/       # Shopping cart CRUD
│   │   │   ├── categories/ # Product category management
│   │   │   ├── checkout/   # Order placement and history
│   │   │   └── products/   # Product catalog
│   │   └── main.py         # FastAPI application entrypoint
│   ├── alembic/            # Database migration scripts
│   ├── tests/              # Backend test suite
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/            # Axios API client and domain services
    │   ├── components/     # Reusable UI components
    │   ├── pages/          # Route-level page components
    │   ├── store/          # State management (Zustand/Context)
    │   ├── types/          # TypeScript interfaces
    │   └── App.tsx
    ├── public/
    └── package.json
```

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3.11+, FastAPI, Uvicorn      |
| ORM         | SQLAlchemy 2.x (async), Alembic     |
| Database    | PostgreSQL 15+                      |
| Auth        | JWT (python-jose), bcrypt           |
| Frontend    | React 18, TypeScript, Vite          |
| HTTP Client | Axios                               |
| Styling     | Tailwind CSS                        |
| Containers  | Docker, Docker Compose              |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) (recommended)
- **Or**, for local development without Docker:
  - Python 3.11+
  - Node.js 18+ and npm/yarn
  - PostgreSQL 15+

---

## Getting Started

### Environment Variables

Copy the example environment file and fill in your values:

```bash
cp backend/.env.example backend/.env
```

Key variables in `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/boots_db

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# App
DEBUG=false
ALLOWED_ORIGINS=http://localhost:3000
```

For the frontend, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

### Running with Docker Compose

```bash
# From the project root
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **Backend** (FastAPI + Uvicorn) on port `8000`
- **Frontend** (Vite dev server) on port `3000`

Migrations run automatically on backend startup.

Access the app at [http://localhost:3000](http://localhost:3000).  
Interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### Running Locally (without Docker)

#### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

---

## Backend Structure

```
backend/app/
├── core/
│   ├── config.py       # Pydantic settings (reads .env)
│   ├── database.py     # Async SQLAlchemy engine and session factory
│   ├── security.py     # JWT creation/decoding, password hashing
│   └── deps.py         # FastAPI dependency injection (get_current_user, get_db)
├── domains/
│   ├── account/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py   # Prefix: /api/v1/account
│   ├── auth/
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py   # Prefix: /api/v1/auth
│   ├── cart/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py   # Prefix: /api/v1/cart
│   ├── categories/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py   # Prefix: /api/v1/categories
│   ├── checkout/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py   # Prefix: /api/v1/checkout
│   └── products/
│       ├── models.py
│       ├── schemas.py
│       ├── service.py
│       └── router.py   # Prefix: /api/v1/products
└── main.py             # App factory, router registration, /health endpoint
```

---

## Frontend Structure

```
frontend/src/
├── api/
│   ├── client.ts       # Axios instance with auth interceptors
│   ├── auth.ts         # Auth API calls
│   ├── products.ts     # Products API calls
│   ├── cart.ts         # Cart API calls
│   ├── categories.ts   # Categories API calls
│   ├── checkout.ts     # Checkout API calls
│   └── account.ts      # Account API calls
├── components/
│   ├── layout/         # Header, Footer, Navigation
│   ├── product/        # ProductCard, ProductGrid, ProductDetail
│   ├── cart/           # CartItem, CartSummary, CartDrawer
│   └── ui/             # Button, Input, Modal, Spinner, etc.
├── pages/
│   ├── HomePage.tsx
│   ├── ProductsPage.tsx
│   ├── ProductDetailPage.tsx
│   ├── CartPage.tsx
│   ├── CheckoutPage.tsx
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── AccountPage.tsx
├── store/
│   ├── authStore.ts    # Auth state (user, tokens)
│   └── cartStore.ts    # Cart state
├── types/
│   └── index.ts        # TypeScript interfaces for all domain entities
├── App.tsx             # Router setup
└── main.tsx            # React entry point
```

---

## API Domains

| Domain       | Base Path            | Description                              |
|--------------|----------------------|------------------------------------------|
| Auth         | `/api/v1/auth`       | Register, login, logout, token refresh   |
| Account      | `/api/v1/account`    | User profile read and update             |
| Products     | `/api/v1/products`   | Product listing, detail, search, filter  |
| Categories   | `/api/v1/categories` | Category listing and hierarchy           |
| Cart         | `/api/v1/cart`       | Add, update, remove cart items           |
| Checkout     | `/api/v1/checkout`   | Place orders, view order history         |
| Health       | `/health`            | Liveness probe (unauthenticated)         |

Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the backend is running.

---

## Database Migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/).

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Downgrade one step
alembic downgrade -1

# View migration history
alembic history
```

> **Note:** The `DATABASE_URL` environment variable must be set before running Alembic commands. The migration runner uses the async `asyncpg` driver automatically.

---

## Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific domain's tests
pytest tests/test_auth.py -v
```

Tests use an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) by default — no PostgreSQL instance is required to run the test suite.

---

## Health Check

The backend exposes an unauthenticated health endpoint at:

```
GET /health
```

Response:

```json
{"status": "ok"}
```

This endpoint is used by Docker health checks, Kubernetes liveness/readiness probes, and load balancer target-group health checks. It is registered directly on the FastAPI app (not under any versioned prefix) and is always available regardless of API version changes.