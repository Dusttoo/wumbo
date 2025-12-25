# Wumbo App

A comprehensive Wumbo management platform that helps households track spending, manage bills, set savings goals, and gain financial clarity through automated bank connections and intuitive interfaces.

## Project Structure

This is a monorepo managed with [Turborepo](https://turbo.build/repo) containing:

```
wumbo/
├── apps/
│   ├── web/              # Next.js web application
│   └── mobile/           # React Native mobile app (Expo)
├── packages/
│   ├── ui/              # Shared UI component library
│   ├── types/           # Shared TypeScript types
│   └── config/          # Shared configuration (ESLint, TypeScript)
├── backend/             # FastAPI backend service
├── worker/              # Celery background worker
├── infrastructure/      # AWS CDK infrastructure code
├── tests/              # End-to-end tests
└── docs/               # Documentation
```

## Quick Start

### Prerequisites

- Node.js 20+ and npm 10+
- Python 3.11+
- Docker and Docker Compose (for local development)
- AWS CLI (for infrastructure deployment)
- Expo CLI (for mobile development)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wumbo
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

4. **Start local services** (Docker Compose)
   ```bash
   cd backend
   docker-compose up -d postgres redis
   ```

5. **Run database migrations**
   ```bash
   cd backend
   alembic upgrade head
   ```

### Development

**Start all services in development mode:**
```bash
npm run dev
```

This starts:
- Web app: http://localhost:3000
- Mobile app: Expo Dev Tools
- Backend: http://localhost:8000 (separate terminal: `cd backend && uvicorn app.main:app --reload`)
- Worker: (separate terminal: `cd worker && celery -A app.worker worker --loglevel=info`)

**Individual services:**
```bash
# Web app only
npm run dev --workspace=@wumbo/web

# Mobile app only
npm run dev --workspace=@wumbo/mobile

# UI library (watch mode)
npm run dev --workspace=@wumbo/ui
```

## Available Scripts

### Root Commands

```bash
npm run dev          # Start all apps in development mode
npm run build        # Build all apps and packages
npm run lint         # Lint all workspaces
npm run format       # Format all code with Prettier
npm run type-check   # Type check all workspaces
npm run test         # Run all tests
npm run clean        # Clean all build artifacts
```

### Backend Commands

```bash
cd backend

# Development
uvicorn app.main:app --reload

# Run tests
pytest

# Linting
ruff check .
ruff format .

# Type checking
mypy app/

# Database migrations
python scripts/run_migrations.py                    # Apply migrations (local)
alembic revision --autogenerate -m "description"    # Create new migration
alembic current                                      # Check current revision
```

### Infrastructure

```bash
cd infrastructure

# Deploy to development
cdk deploy -c environment=development --all

# Deploy specific stack
cdk deploy -c environment=development development-DatabaseStack

# View infrastructure changes
cdk diff -c environment=development

# Destroy infrastructure (careful!)
cdk destroy -c environment=development --all
```

### Mobile App Builds

```bash
cd apps/mobile

# Development builds
make dev-ios          # iOS development build
make dev-android      # Android development build

# Production builds (requires confirmation)
make prod-ios         # iOS production build
make prod-android     # Android production build
```

See [BUILD.md](./apps/mobile/BUILD.md) for complete build documentation.

## Documentation

### Project Documentation
- **[Implementation Plan](./plan.md)** - Complete project roadmap and features
- **[Infrastructure Architecture](./infrastructure/README.md)** - AWS CDK infrastructure deployment guide
- **[Monitoring Stack](./infrastructure/MONITORING.md)** - Prometheus/Grafana observability setup
- **[Database Migrations](./backend/MIGRATIONS.md)** - Alembic migration management guide
- **[Mobile App Builds](./apps/mobile/BUILD.md)** - EAS build and deployment guide

### Design & Strategy
- **[CI/CD Strategy](./docs/CICD_STRATEGY.md)** - Deployment pipeline and workflows
- **[Design System](./docs/DESIGN_SYSTEM.md)** - UI component library guidelines
- **[Setup for Success](./docs/SETUP_FOR_SUCCESS.md)** - Complete setup summary

## Architecture

### Frontend
- **Web**: Next.js 14+ (App Router, React Server Components)
- **Mobile**: React Native with Expo
- **Shared UI**: Cross-platform component library
- **State**: Zustand
- **Styling**: Tailwind CSS (web), NativeWind (mobile)

### Backend
- **API**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via SQLAlchemy + Alembic)
- **Cache**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT-based custom auth

### Infrastructure (AWS CDK)
1. **SecurityStack** - VPC, Secrets Manager, KMS encryption
2. **EcrStack** - Container registries for Docker images
3. **DatabaseStack** - RDS PostgreSQL 16 with Graviton instances
4. **CacheStack** - ElastiCache Redis 7.1 for caching and Celery broker
5. **DnsStack** - Route53 hosted zones and ACM SSL certificates (optional)
6. **ComputeStack** - ECS Fargate services (Backend API, Celery Worker, Celery Beat, Migration Task)
7. **MonitoringStack** - Prometheus, Grafana, CloudWatch Alarms, and SNS notifications

## Tech Stack

| Category | Technology |
|----------|-----------|
| Frontend (Web) | Next.js, React, TypeScript, Tailwind CSS |
| Frontend (Mobile) | React Native, Expo, TypeScript, NativeWind |
| Backend | FastAPI, Python, SQLAlchemy, Pydantic |
| Database | PostgreSQL 16, Redis 7.1, Alembic (migrations) |
| Infrastructure | AWS CDK, ECS Fargate, RDS, ElastiCache, Route53, ACM |
| Security | Fernet encryption, JWT auth, webhook verification, KMS |
| Monitoring | Prometheus, Grafana, CloudWatch, SNS |
| CI/CD | GitHub Actions, EAS Build |
| Testing | Jest, Pytest, Playwright |

## Key Features

### Financial Management
- 💳 **Transaction Tracking** - Automatic import via Plaid + manual entry
- 📊 **Budgets** - Category-based budgets with alerts
- 📅 **Bills & Subscriptions** - Track recurring payments
- 🎯 **Savings Goals** - Set and monitor progress
- 🏠 **Multi-User Households** - Share finances with family
- 📈 **Analytics** - Spending trends and insights

### Platform & Security
- 📱 **Mobile & Web** - Access from anywhere with native apps
- 🔔 **Notifications** - Bill reminders and budget alerts
- 🔒 **Bank-Level Security** - Encrypted data storage, webhook verification
- 🔐 **SSL/TLS** - HTTPS with custom domains
- 📊 **Observability** - Prometheus metrics and Grafana dashboards
- 🚀 **Production-Ready** - Automated migrations, monitoring, and alerts

## Development Workflow

### Creating a New Feature

1. Create a feature branch
   ```bash
   git checkout -b feature/add-budget-alerts
   ```

2. Make your changes
   - Backend: Add endpoints, tests
   - Frontend: Add UI components, pages
   - Shared: Update types if needed

3. Run quality checks
   ```bash
   npm run lint
   npm run type-check
   npm run test
   ```

4. Commit and push
   ```bash
   git add .
   git commit -m "feat: add budget alert notifications"
   git push origin feature/add-budget-alerts
   ```

5. Create Pull Request
   - PR checks will run automatically
   - Wait for review and approval
   - Merge to `development` branch

### Deployment

- **Development**: Auto-deploys on push to `development` branch
- **Staging**: Auto-deploys on push to `staging` branch
- **Production**: Auto-deploys on push to `main` branch (requires approval)

See [CI/CD Strategy](./docs/CICD_STRATEGY.md) for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

Private - All rights reserved

## Support

For questions or issues:
- Check the [documentation](./docs/)
- Review [existing issues](https://github.com/your-org/wumbo/issues)
- Create a new issue

---

**Built with ❤️ for better family financial management**
