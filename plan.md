# Wumbo App - Implementation Plan

## Vision
A comprehensive Wumbo management platform that helps households track spending, manage bills, set savings goals, and gain financial clarity through automated bank connections and intuitive interfaces.

## Project Goals
- **Primary Users**: Personal use initially, with architecture for public offering
- **Platforms**: Web (Next.js) + Native Mobile (React Native) from start
- **Approach**: Comprehensive v1 with core features fully implemented
- **Scale**: Multi-tenant architecture supporting multiple households

---

## Technology Stack

### Infrastructure (AWS)
- **Hosting**: AWS Amplify (frontend) + ECS Fargate (backend)
- **Infrastructure as Code**: AWS CDK (Python 3.11+) - modular stack architecture
- **Database**: Amazon RDS PostgreSQL 16 (Graviton instances)
- **Storage**: S3 for file uploads/exports, EFS for monitoring data
- **Notifications**:
  - Amazon SES (email)
  - Amazon SNS (push notifications and alarms)
- **Cache**: Amazon ElastiCache Redis 7.1 for sessions, rate limiting, and Celery broker
- **Secrets Management**: AWS Secrets Manager with KMS encryption
- **DNS & SSL**: Route53 hosted zones + ACM SSL certificates
- **Monitoring**: Prometheus + Grafana + CloudWatch Alarms + CloudWatch Logs

**Note**: Infrastructure follows proven patterns from cipher-dnd-bot project. See [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) for detailed architecture.

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **API**: RESTful with potential GraphQL layer later
- **Authentication**: Custom JWT-based auth
- **ORM**: SQLAlchemy with Alembic migrations
- **Task Queue**: Celery with Redis
- **Integrations**: Plaid API for bank connections

### Frontend
- **Web**: Next.js 14+ (App Router, React Server Components)
- **Mobile**: React Native with Expo
- **Shared Component Library**: Cross-platform UI components (see Design System below)
- **State Management**: Zustand or React Query
- **UI Framework**: Tailwind CSS + shadcn/ui (web), NativeWind (mobile)
- **Charts**: Recharts (web), Victory Native (mobile)

### Development Tools
- **Monorepo**: Turborepo or Nx
- **Type Safety**: TypeScript (frontend), Pydantic (backend)
- **Testing**: Jest, Pytest, Playwright
- **CI/CD**: GitHub Actions - See [CI/CD Strategy](./docs/CICD_STRATEGY.md)
  - Main deployment pipeline (deploy.yml)
  - Pull request checks (pr.yml)
  - Mobile app builds (mobile.yml)
  - Path-based filtering for efficient builds
  - Multi-environment support (dev/staging/prod)
  - Automated deployments with approval gates
- **Code Quality**: ESLint, Prettier, Ruff (Python)

### Design System & Style Consistency

**Goal**: Maintain consistent visual design and UX across web and mobile platforms.

**Approach**:
- Shared component library in monorepo (`packages/ui`)
- Platform-agnostic design tokens (colors, spacing, typography)
- Consistent component APIs across web and mobile
- Design standards document (to be created during Phase 1)

**Component Library Structure**:
```
packages/
  ui/
    ├── tokens/              # Design tokens (colors, spacing, fonts)
    │   ├── colors.ts       # Brand colors, semantic colors
    │   ├── spacing.ts      # Spacing scale (4px base)
    │   ├── typography.ts   # Font families, sizes, weights
    │   └── index.ts
    ├── components/         # Shared components
    │   ├── Button/
    │   ├── Input/
    │   ├── Card/
    │   ├── Badge/
    │   └── ...
    ├── web/                # Web-specific implementations
    └── mobile/             # Mobile-specific implementations
```

**Design Standards** (to be defined):
- Color palette (primary, secondary, accent, semantic colors)
- Typography scale (headings, body, labels)
- Spacing system (consistent margins, padding)
- Component variations (sizes: sm, md, lg)
- Animation/transition standards
- Accessibility requirements (WCAG 2.1 AA)
- Dark mode support

**Cross-Platform Component Example**:
```typescript
// Shared API, platform-specific implementation
<Button
  variant="primary"
  size="md"
  onPress={handlePress}
>
  Add Transaction
</Button>
```

**Benefits**:
- Consistent user experience across platforms
- Faster development (reuse components)
- Single source of truth for design
- Easier to maintain and update designs
- Type-safe component props

---

## Core Features

### 1. Transaction Management
- Automatic import via Plaid
- Manual transaction entry
- Transaction categorization (auto + manual)
- Custom category creation and management
- Transaction search and filtering
- Bulk operations (recategorize, delete, etc.)

### 2. Bill & Subscription Tracking
- Manual bill creation with due dates
- Link transactions to bills
- Recurring bill/subscription detection
- Bill payment status tracking
- Calendar view of upcoming bills
- Bill reminders (email + push)

### 3. Budget Management
- Category-based budgets
- Monthly/custom period budgets
- Budget vs. actual tracking
- Budget alerts when approaching/exceeding limits
- Rollover budget options
- Split budgets (individual vs. household)

### 4. Savings Goals
- Create multiple savings goals
- Target amount and date
- Link transactions as contributions
- Progress tracking
- Goal prioritization
- Visual progress indicators

### 5. Bank Account Management
- Connect multiple bank accounts via Plaid
- Select which accounts contribute to household budget
- Account balance tracking
- Account refresh and sync
- Account status monitoring

### 6. Multi-User Household
- Household creation and management
- User invitation system
- Role-based access (Admin, Member)
- Future: Granular permissions
- Individual vs. shared budgets/goals
- Activity audit log

### 7. Dashboard & Reporting
- Quick overview of financial health
- Upcoming bills in next 30 days
- Budget status by category
- Savings goal progress
- Recent transactions
- Spending trends (basic charts)
- Export to CSV/PDF

### 8. Notifications
- Email notifications (SES)
- Push notifications (SNS)
- Configurable notification preferences
- Notification types:
  - Bills due soon
  - Budget alerts
  - Unusual spending
  - Goal milestones
  - Account sync issues

---

## Database Schema Overview

### Core Tables

**users**
- id, email, password_hash, name, created_at, updated_at
- notification_preferences (JSONB)
- last_login

**households**
- id, name, created_at, updated_at
- settings (JSONB)

**household_members**
- id, household_id, user_id, role (admin/member)
- invited_at, joined_at, invited_by
- permissions (JSONB - for future granular control)

**bank_accounts**
- id, household_id, user_id (who connected it)
- plaid_account_id, plaid_item_id
- name, official_name, type, subtype
- current_balance, available_balance
- include_in_budget (boolean)
- last_synced_at, created_at

**categories**
- id, household_id, name, type (income/expense)
- color, icon, parent_category_id
- is_system (boolean), created_at

**transactions**
- id, account_id, household_id
- plaid_transaction_id, amount, date
- name, merchant_name, category_id
- pending, is_manual
- notes, created_at, updated_at

**budgets**
- id, household_id, category_id
- amount, period_type (monthly/custom)
- start_date, end_date
- rollover_enabled, created_at

**bills**
- id, household_id, name, amount
- due_date, recurrence_rule (RRULE)
- category_id, is_automatic
- reminder_days_before, created_at

**bill_transactions**
- bill_id, transaction_id
- linked_at

**savings_goals**
- id, household_id, name, target_amount
- current_amount, target_date
- category_id, priority, created_at

**goal_contributions**
- goal_id, transaction_id
- amount, contributed_at

**notifications**
- id, user_id, type, title, message
- read_at, sent_at, delivery_status

---

## Architecture & Infrastructure

### AWS Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CloudFront CDN                      │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Amplify Hosting    │      │   Application LB     │
│   (Next.js Web)      │      │                      │
└──────────────────────┘      └──────────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                              ▼                     ▼
                    ┌─────────────────┐   ┌─────────────────┐
                    │  ECS Fargate    │   │  ECS Fargate    │
                    │  (FastAPI)      │   │  (Celery)       │
                    └─────────────────┘   └─────────────────┘
                              │                     │
                    ┌─────────┴──────────┬──────────┘
                    │                    │
                    ▼                    ▼
          ┌──────────────────┐  ┌──────────────────┐
          │   RDS Postgres   │  │  ElastiCache     │
          │                  │  │  (Redis)         │
          └──────────────────┘  └──────────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │  SES / SNS       │
          │  (Notifications) │
          └──────────────────┘
```

### CDK Structure (Python-based) ✅ IMPLEMENTED
```
infrastructure/
├── stacks/
│   ├── __init__.py
│   ├── security_stack.py         # ✅ VPC, Secrets Manager, KMS encryption
│   ├── ecr_stack.py              # ✅ Container registries for Docker images
│   ├── database_stack.py         # ✅ RDS PostgreSQL 16 with Graviton
│   ├── cache_stack.py            # ✅ ElastiCache Redis 7.1
│   ├── dns_stack.py              # ✅ Route53 hosted zones, ACM SSL certificates
│   ├── compute_stack.py          # ✅ ECS Fargate (backend, worker, beat, migrations)
│   ├── monitoring_stack.py       # ✅ Prometheus, Grafana, CloudWatch, SNS
│   └── (storage/notification)    # Future: S3 buckets, SES setup
├── scripts/
│   ├── run-migration-task.sh     # ✅ ECS migration task runner
│   └── (future utilities)
├── app.py                        # ✅ Main CDK app entry point
├── requirements.txt              # ✅ Python dependencies
├── cdk.json                      # ✅ CDK configuration with env-specific settings
├── README.md                     # ✅ Complete setup and deployment guide
└── MONITORING.md                 # ✅ Prometheus/Grafana documentation
```

See [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) for complete infrastructure documentation including:
- Detailed stack breakdown and dependencies
- Resource specifications per environment
- Secrets management guide
- Cost optimization strategies
- Deployment procedures

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Infrastructure Setup** ✅ COMPLETE
- [x] Initialize monorepo (Turborepo)
- [x] Set up AWS CDK project (7 stacks implemented)
- [x] Deploy VPC and networking (SecurityStack)
- [x] Deploy RDS PostgreSQL 16 with Graviton instances (DatabaseStack)
- [x] Deploy Redis 7.1 ElastiCache (CacheStack)
- [x] Deploy ECR container registries (EcrStack)
- [x] Deploy Route53 + ACM SSL certificates (DnsStack - optional)
- [x] Deploy ECS Fargate services (ComputeStack)
- [x] Deploy Prometheus + Grafana monitoring (MonitoringStack)
- [x] Implement automated database migrations (ECS task + GitHub Actions)
- [x] **Set up CI/CD pipeline (GitHub Actions)** - See [CI/CD Strategy](./docs/CICD_STRATEGY.md)
  - [x] Configure migration workflow (run-migrations.yml)
  - [ ] Configure main deployment workflow (deploy.yml) - TODO
  - [ ] Configure PR checks workflow (pr.yml) - TODO
  - [x] Configure mobile app build workflow (eas.json + Makefile)
  - [ ] Set up GitHub environments (dev, staging, production) - TODO
  - [ ] Configure AWS credentials and secrets - TODO
  - [ ] Test deployment to development environment - TODO

**Backend Foundation**
- [x] Initialize FastAPI project structure
- [x] Set up SQLAlchemy models
- [x] Create Alembic migration system
- [x] Implement JWT authentication system
  - User registration
  - Login/logout
  - Token refresh
  - Password reset
- [ ] Create user CRUD endpoints
- [ ] Set up Celery for background tasks
- [ ] Configure logging and error handling

**Frontend Foundation**
- [x] Initialize Next.js project (App Router)
- [x] Initialize React Native project (Expo)
- [ ] Set up shared UI component library (`packages/ui`)
  - Create design tokens (colors, spacing, typography)
  - Define design standards document
  - Set up platform-specific implementations (web/mobile)
  - Create initial core components (Button, Input, Card)
- [ ] Create authentication pages/screens
  - Login
  - Register
  - Password reset
- [ ] Implement auth state management
- [ ] Create base layout and navigation
- [ ] Set up API client with auth interceptors

**Design System**
- [x] Create design standards document (to be finalized during implementation)
  - Color palette definition
  - Typography scale
  - Spacing system
  - Component size variants
  - Accessibility guidelines
  - Dark mode strategy
- [ ] Set up Storybook for component documentation (optional but recommended)
- [ ] Establish component development workflow

**Database**
- [ ] Create initial schema (users, households, household_members)
- [ ] Write seed data for development
- [ ] Set up automated backups

### Phase 2: Core Account & Transaction Features (Weeks 4-6)

**Backend**
- [x] Implement Plaid integration
  - Link Token creation
  - Public Token exchange
  - Account/transaction sync
  - Webhook handlers
- [ ] Bank account endpoints
  - List accounts
  - Connect account
  - Update account settings
  - Remove account
- [ ] Transaction endpoints
  - List/filter/search transactions
  - Create manual transaction
  - Update transaction (category, notes)
  - Bulk operations
- [ ] Category endpoints
  - List categories
  - Create custom category
  - Update/delete category
- [ ] Scheduled task: Daily Plaid sync

**Frontend (Web + Mobile)**
- [ ] Household setup flow
- [ ] Bank account connection flow (Plaid Link)
- [ ] Bank accounts dashboard
- [ ] Transactions list with filtering
- [ ] Transaction detail view/edit
- [ ] Category management
- [ ] Manual transaction creation

**Database**
- [ ] Add tables: bank_accounts, categories, transactions
- [ ] Create indexes for performance
- [ ] Add data validation constraints

### Phase 3: Budgets & Bills (Weeks 7-9)

**Backend**
- [ ] Budget endpoints
  - Create/update/delete budget
  - Get budget status (spent vs. limit)
  - Budget history
- [ ] Bill endpoints
  - Create/update/delete bill
  - Link transactions to bills
  - Get upcoming bills
  - Mark bill as paid
- [ ] Recurring bill detection logic
- [ ] Bill reminder notifications (Celery task)
- [ ] Budget alert notifications

**Frontend (Web + Mobile)**
- [ ] Budget creation and management
- [ ] Budget dashboard with progress bars
- [ ] Bill management interface
- [ ] Bill calendar view
- [ ] Transaction-to-bill linking interface
- [ ] Budget alerts display

**Database**
- [ ] Add tables: budgets, bills, bill_transactions
- [ ] Create recurrence rule handling

### Phase 4: Savings Goals & Advanced Features (Weeks 10-12)

**Backend**
- [ ] Savings goal endpoints
  - Create/update/delete goal
  - Link contributions
  - Get goal progress
- [ ] Dashboard summary endpoint
- [ ] Spending trends/analytics endpoints
- [ ] Export endpoints (CSV, PDF)
- [ ] Notification preference endpoints
- [ ] Push notification service

**Frontend (Web + Mobile)**
- [ ] Savings goals interface
- [ ] Goal progress tracking
- [ ] Main dashboard with overview
- [ ] Basic charts (spending by category, trends)
- [ ] Notification preferences page
- [ ] Export functionality
- [ ] Push notification registration

**Database**
- [ ] Add tables: savings_goals, goal_contributions, notifications
- [ ] Optimize queries for dashboard

### Phase 5: Multi-User & Polish (Weeks 13-15)

**Backend**
- [ ] Household invitation system
- [ ] Role-based access control
- [ ] Activity audit logging
- [ ] User management endpoints (for admins)
- [ ] Data isolation enforcement
- [ ] Rate limiting
- [ ] API documentation (OpenAPI/Swagger)

**Frontend (Web + Mobile)**
- [ ] Household member management
- [ ] User invitation flow
- [ ] Role management interface
- [ ] Profile settings
- [ ] App onboarding/tutorial
- [ ] Loading states and error boundaries
- [ ] Responsive design refinement
- [ ] Accessibility improvements

**Testing & Quality**
- [ ] Backend unit tests (>80% coverage)
- [ ] Frontend component tests
- [ ] E2E tests (critical flows)
- [ ] Performance testing
- [ ] Security audit
- [ ] Penetration testing (basic)

### Phase 6: Deployment & Launch Prep (Week 16+)

**Infrastructure** 🚧 IN PROGRESS
- [x] Production environment setup (7 CDK stacks ready)
- [x] SSL certificates (ACM with DNS validation)
- [x] Domain configuration (Route53 hosted zones)
- [ ] CloudFront CDN setup (future optimization)
- [x] Monitoring and alerting (Prometheus + Grafana + CloudWatch)
- [x] Database migration automation (ECS task + GitHub Actions)
- [ ] Backup verification (RDS automated backups configured, needs testing)
- [ ] Disaster recovery plan (needs documentation)

**Launch Preparation**
- [ ] User documentation
- [ ] Privacy policy
- [ ] Terms of service
- [ ] App store submissions (iOS/Android)
- [ ] Beta testing with friends/family
- [ ] Performance optimization
- [ ] Final security review

---

## Security Considerations

### Authentication & Authorization
- JWT tokens with short expiration (15 min access, 7 day refresh)
- Secure password hashing (bcrypt, cost factor 12+)
- Rate limiting on auth endpoints
- Email verification for new accounts
- 2FA option (future enhancement)
- Session invalidation on password change

### Data Protection ✅ ENHANCED
- Encryption at rest (RDS, S3, EFS with KMS)
- Encryption in transit (TLS 1.3 with ACM certificates)
- ✅ **Fernet encryption for sensitive data** (bank access tokens)
  - Symmetric encryption using cryptography library
  - Automatic encryption/decryption via SQLAlchemy TypeDecorator
  - Encryption keys stored in AWS Secrets Manager
- Regular security patches
- Principle of least privilege (IAM roles)
- Input validation and sanitization
- SQL injection prevention (ORM parameterization)
- XSS prevention
- CSRF protection

### Plaid Security ✅ IMPLEMENTED
- ✅ **Store access tokens encrypted** (Fernet encryption in database)
- ✅ **Webhook signature verification** (JWT verification with body hash)
  - Validates webhook authenticity
  - Prevents replay attacks (timestamp checking)
  - Ensures request integrity (SHA-256 body hash)
- Use Plaid webhooks for real-time updates
- Handle token rotation
- Monitor for unusual API usage
- Implement proper error handling (don't leak info)

### Multi-Tenancy
- Strict data isolation by household_id
- Row-level security policies
- Audit logging for sensitive operations
- User impersonation protection

---

## Testing Strategy

### Backend Testing
- **Unit Tests**: All business logic, utilities
- **Integration Tests**: Database operations, external APIs
- **API Tests**: All endpoints with various scenarios
- **Load Tests**: Expected concurrent users (start with 100)

### Frontend Testing
- **Component Tests**: All reusable components
- **Integration Tests**: Page flows
- **E2E Tests**: Critical user journeys
  - Sign up → connect bank → view transactions
  - Create budget → receive alert
  - Create bill → link transaction

### Mobile Testing
- **Device Testing**: iOS (latest 2 versions), Android (latest 3)
- **Responsive Testing**: Various screen sizes
- **Offline Behavior**: Handle network issues gracefully

---

## Deployment Strategy

### Environments
1. **Development**: Local development + dev AWS
2. **Staging**: Production-like for testing
3. **Production**: Live user environment

### CI/CD Pipeline
```
GitHub Push →
  Run Tests →
  Build Docker Images →
  Push to ECR →
  Deploy to ECS (staging) →
  Run E2E Tests →
  Manual Approval →
  Deploy to Production
```

### Rollback Plan
- Keep last 3 task definitions
- Database migrations must be backward compatible
- Feature flags for gradual rollouts
- Monitoring for error rate spikes

---

## Monitoring & Observability ✅ IMPLEMENTED

### Monitoring Stack (Prometheus + Grafana)
- ✅ **Prometheus** - Time-series metrics collection and storage
  - 15-day metrics retention
  - Service discovery via AWS Cloud Map
  - EFS persistent storage
  - Scrapes backend, worker, and beat services
- ✅ **Grafana** - Metrics visualization and dashboarding
  - Public access via Application Load Balancer
  - Pre-configured Prometheus data source
  - EFS persistent storage for dashboards
  - Default admin credentials (changeme - must update!)
- ✅ **CloudWatch Alarms** - Automated alerting
  - Backend CPU > 80%
  - Backend Memory > 80%
  - Database CPU > 80%
  - Database Connections > 80
- ✅ **SNS Notifications** - Email alerts for critical events
  - Configurable per environment
  - Extensible to Slack, PagerDuty, etc.

### Metrics to Track
- API response times (p50, p95, p99)
- Error rates by endpoint
- Database query performance
- Plaid API success/failure rates
- User sign-ups and active users
- Transaction sync success rates
- Notification delivery rates
- ECS task health and resource utilization
- Database connections and query performance
- Redis cache hit rates

### CloudWatch Logs
- `/aws/ecs/{env}-wumbo-cluster/backend` - Backend API logs
- `/aws/ecs/{env}-wumbo-cluster/worker` - Celery worker logs
- `/aws/ecs/{env}-wumbo-cluster/beat` - Celery beat scheduler logs
- `/aws/ecs/{env}-wumbo-cluster/migration` - Database migration logs
- `/aws/ecs/{env}-wumbo-cluster/prometheus` - Prometheus logs
- `/aws/ecs/{env}-wumbo-cluster/grafana` - Grafana logs

### Logging
- Structured JSON logs
- Log levels: DEBUG (dev), INFO (staging), WARN/ERROR (prod)
- Request/response logging (sanitized)
- Performance logging for slow queries
- 7-day retention for cost optimization

---

## Cost Estimates (Monthly) - UPDATED

### AWS Development Environment
- NAT Gateway: ~$32/month
- RDS PostgreSQL t4g.micro: ~$12/month
- ElastiCache t4g.micro: ~$12/month
- ECS Fargate (5 services): ~$40-50/month
- EFS (monitoring): ~$5/month
- CloudWatch Logs: ~$5/month
- **Total AWS (Development)**: ~$100-110/month

### AWS Production Environment
- NAT Gateways (2 for HA): ~$64/month
- RDS PostgreSQL t4g.small (Multi-AZ): ~$50/month
- ElastiCache r7g.large: ~$106/month
- ECS Fargate (8-12 tasks): ~$120-180/month
- EFS (monitoring): ~$10/month
- ALB (Grafana): ~$16/month
- CloudWatch: ~$10/month
- Route53 + ACM: ~$1/month (if using custom domain)
- **Total AWS (Production)**: ~$370-430/month

### Third-Party Services
- Plaid (Development): Free (100 items)
- Plaid (Production): $0.25-1/account/month
- Domain: ~$12/year (~$1/month)
- **Estimate for 2 users (Production)**: ~$380-440/month

### Scaling Costs (100 households ~300 users)
- Larger RDS instance (r7g.large Multi-AZ): ~$200
- More ECS capacity (auto-scaling): ~$300-400
- ElastiCache (larger instance): ~$150
- Plaid costs: ~$150-300 (assuming avg 2 accounts/user)
- Additional monitoring/logging: ~$50
- **Total**: ~$850-1,100/month

---

## Future Enhancements

### Features
- [ ] Debt tracking and payoff planning
- [ ] Investment account tracking (read-only)
- [ ] Tax category tagging
- [ ] Receipt photo uploads and OCR
- [ ] Smart insights and recommendations
- [ ] Spending predictions using ML
- [ ] Bill negotiation assistant
- [ ] Financial goal templates
- [ ] Net worth tracking over time
- [ ] Multi-currency support

### Technical
- [ ] GraphQL API option
- [ ] Real-time updates (WebSockets)
- [ ] Offline mode for mobile
- [ ] Two-factor authentication
- [ ] Granular permission system
- [ ] API for third-party integrations
- [ ] White-label option for B2B
- [ ] Advanced caching strategy
- [ ] Database read replicas
- [ ] Multi-region deployment

---

## Open Questions & Decisions Needed

1. **Mobile App Distribution**
   - Submit to App Store/Play Store immediately or start with TestFlight/Beta?
   - Organization account needed for App Store ($99/year)

2. **Email Service**
   - Start with SES or use SendGrid/Mailgun for better deliverability?

3. **Error Tracking**
   - Use Sentry for error monitoring? (~$26/month)

4. **Analytics**
   - Add usage analytics (Mixpanel, Amplitude)?
   - Privacy considerations for user tracking

5. **Database Backups**
   - Retention policy? (Suggest: Daily for 7 days, weekly for 4 weeks)

6. **Plaid vs Alternatives**
   - Stick with Plaid or evaluate Yodlee, Finicity, Teller?
   - Consider costs at scale

7. **Feature Priorities**
   - Which features from Phase 4-5 are must-haves for v1?
   - Any features that can be deferred?

---

## Getting Started

### Prerequisites
- AWS Account with appropriate permissions
- Node.js 20+ and Python 3.11+
- Docker and Docker Compose
- Plaid account (development keys)
- GitHub account for CI/CD

### Initial Setup Commands
```bash
# Clone repository structure
mkdir wumbo && cd wumbo

# Initialize monorepo
npx create-turbo@latest

# Set up infrastructure
mkdir infrastructure && cd infrastructure
npx aws-cdk init app --language typescript

# Set up backend
mkdir backend && cd backend
poetry init
poetry add fastapi sqlalchemy alembic plaid-python

# Set up web frontend
npx create-next-app@latest web --typescript --tailwind --app

# Set up mobile
npx create-expo-app mobile --template
```

### Development Workflow
1. Start local PostgreSQL and Redis (Docker Compose)
2. Run database migrations
3. Start backend (FastAPI dev server)
4. Start web frontend (Next.js dev server)
5. Start mobile (Expo)
6. Use Plaid sandbox for testing

---

## Success Criteria

### MVP Success
- ✅ Users can sign up and create household
- ✅ Connect bank accounts via Plaid
- ✅ View and categorize transactions
- ✅ Create and track budgets
- ✅ Add and track bills
- ✅ Set and monitor savings goals
- ✅ Receive bill reminders
- ✅ Access via web and mobile app

### Quality Metrics
- API response time < 500ms (p95)
- Frontend load time < 2s
- Mobile app size < 50MB
- Test coverage > 80%
- Zero critical security vulnerabilities
- Plaid sync success rate > 95%

### User Experience
- Onboarding complete in < 10 minutes
- Daily active usage > 5 minutes
- User satisfaction score > 4/5
- Low support ticket volume

---

*This plan is a living document and will be updated as the project evolves.*
