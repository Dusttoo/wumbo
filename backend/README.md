# Wumbo Backend API

FastAPI backend for the Wumbo application.

## Features

- FastAPI with async support
- SQLAlchemy 2.0 ORM
- Alembic database migrations
- JWT authentication
- PostgreSQL database
- Redis caching
- Celery task queue
- Plaid integration for bank connections
- AWS integration (S3, SES, SNS)

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

## Local Development Setup

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your local configuration
```

### 4. Set up database

```bash
# Start PostgreSQL (or use docker-compose)
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head
```

### 5. Run the application

```bash
# Development mode with hot reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/api/v1/docs
- API Docs (ReDoc): http://localhost:8000/api/v1/redoc

## Docker Development

```bash
# Build and run with docker-compose
docker-compose up --build

# Run migrations in container
docker-compose exec backend alembic upgrade head
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_users.py
```

## Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy app
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
│   ├── versions/         # Migration files
│   └── env.py           # Alembic config
├── app/
│   ├── api/             # API endpoints
│   │   ├── endpoints/   # Route handlers
│   │   └── deps/        # Dependencies (auth, etc.)
│   ├── core/            # Core utilities
│   │   ├── config.py    # Settings
│   │   ├── security.py  # Auth utilities
│   │   └── logging.py   # Logging setup
│   ├── db/              # Database setup
│   │   ├── base.py      # Base model
│   │   └── session.py   # DB session
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── middleware/      # Custom middleware
├── tests/               # Test files
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Example environment variables
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token

### Users

- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `GET /api/v1/users/{user_id}` - Get user by ID

### Health

- `GET /health` - Health check endpoint

## Environment Variables

See `.env.example` for all available environment variables.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT signing key (use strong random value)
- `PLAID_CLIENT_ID` - Plaid API client ID
- `PLAID_SECRET` - Plaid API secret
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials

## Deployment

The backend is containerized and deployed to AWS ECS Fargate. See the `infrastructure/` directory for CDK deployment configuration.

## License

Private - Wumbo Application
