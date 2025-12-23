# Family Budget App - Infrastructure Architecture

This document outlines the CDK infrastructure structure, following the proven patterns from cipher-dnd-bot but tailored for the family budget application.

## Infrastructure Overview

**Language**: Python 3.11+ with AWS CDK
**Pattern**: Modular stacks with explicit dependencies
**Environments**: development, staging, production

## Directory Structure

```
infrastructure/
├── app.py                          # Main CDK app entry point
├── requirements.txt                # Python dependencies
├── cdk.json                        # CDK configuration
├── cdk.context.json                # Environment-specific config (gitignored sensitive values)
├── Makefile                        # Deployment shortcuts
├── README.md                       # Setup and deployment instructions
├── SECRETS_SETUP.md               # Guide for populating secrets
├── scripts/
│   ├── populate-secrets.py        # Script to create/update secrets in AWS
│   └── verify-deployment.py       # Post-deployment verification
└── stacks/
    ├── __init__.py
    ├── security_stack.py          # VPC, Secrets, KMS
    ├── ecr_stack.py              # Container registries
    ├── storage_stack.py          # S3 buckets
    ├── database_stack.py         # RDS PostgreSQL
    ├── cache_stack.py            # ElastiCache Redis
    ├── dns_stack.py              # Route53, ACM certificates
    ├── compute_stack.py          # ECS Fargate services
    ├── notification_stack.py     # SES, SNS
    ├── monitoring_stack.py       # Prometheus, Grafana, critical alarms
    └── iam_policies.py           # Shared IAM policy definitions
```

## Stack Breakdown

### 1. SecurityStack (VPC, Secrets, KMS)
**Purpose**: Foundation security resources
**Dependencies**: None (deployed first)

**Resources**:
- VPC with 3-tier subnet architecture:
  - Public subnets (ALB, NAT Gateway)
  - Private subnets with egress (ECS tasks, Lambda)
  - Isolated subnets (RDS)
- VPC Endpoints (S3, ECR, Secrets Manager, SES)
- VPC Flow Logs (staging/production only)
- KMS encryption keys (production only)
- Secrets Manager secrets:
  - `{env}/family-budget/database` - DB credentials
  - `{env}/family-budget/plaid` - Plaid API keys
  - `{env}/family-budget/jwt` - JWT signing keys
  - `{env}/family-budget/external-services` - Other API keys

**Exports**:
- VPC ID and subnet IDs
- Security group references
- Secret ARNs

**NAT Configuration**:
- Development: 1 NAT Gateway
- Staging: 1 NAT Gateway
- Production: 2 NAT Gateways (HA)

---

### 2. EcrStack (Container Registries)
**Purpose**: Docker image repositories
**Dependencies**: None (can deploy in parallel with Security)

**Resources**:
- ECR repositories:
  - `{env}/family-budget/backend` - FastAPI backend
  - `{env}/family-budget/frontend` - Next.js web frontend
  - `{env}/family-budget/worker` - Celery worker
  - `{env}/family-budget/migrations` - Alembic migration runner

**Repository Settings**:
- Image scanning on push
- Lifecycle policy (keep last 10 images)
- Immutable tags (production only)
- Encryption at rest

**Exports**:
- Repository URIs

---

### 3. StorageStack (S3 Buckets)
**Purpose**: Object storage for uploads and exports
**Dependencies**: None (can deploy in parallel)

**Resources**:
- S3 buckets:
  - `{env}-family-budget-exports` - CSV/PDF exports
    - Lifecycle: Delete after 30 days
    - CORS enabled for web uploads
  - `{env}-family-budget-receipts` - Receipt photo uploads
    - Lifecycle: Transition to Glacier after 90 days
  - `{env}-family-budget-backups` - Database backups
    - Lifecycle: Retain 30 days, then delete
    - Versioning enabled (production)

**Security**:
- Block public access
- Encryption at rest (SSE-S3)
- Access logging (production)
- Bucket policies for ECS task role access

**Exports**:
- Bucket names and ARNs

---

### 4. DatabaseStack (RDS PostgreSQL)
**Purpose**: Primary database
**Dependencies**: SecurityStack (VPC)

**Resources**:
- RDS PostgreSQL 15.x
  - Development: db.t4g.micro (1 vCPU, 1GB RAM)
  - Staging: db.t4g.small (2 vCPU, 2GB RAM)
  - Production: db.t4g.medium (2 vCPU, 4GB RAM)
- Auto-scaling storage (starts at 20GB)
- Automated backups:
  - Development: 7 days retention
  - Staging: 14 days retention
  - Production: 30 days retention
- Security group (port 5432 access from private subnets)
- Secrets Manager rotation (production, every 30 days)
- Multi-AZ deployment (production only)

**Database Configuration**:
- Database name: `family_budget`
- Username: `dbadmin` (stored in Secrets Manager)
- SSL/TLS required connections
- CloudWatch log exports (PostgreSQL logs)

**Exports**:
- Database endpoint
- Database port
- Secret ARN
- Security group ID

---

### 5. CacheStack (ElastiCache Redis)
**Purpose**: Session storage, rate limiting, task queue
**Dependencies**: SecurityStack (VPC)

**Resources**:
- ElastiCache Redis 7.x
  - Development: cache.t4g.micro (0.5GB)
  - Staging: cache.t4g.small (1.37GB)
  - Production: cache.t4g.medium (3.09GB)
- Security group (port 6379 access from private subnets)
- Automatic failover (production only)
- Encryption in transit
- Encryption at rest (production only)

**Use Cases**:
- Session storage (JWT refresh token tracking)
- Rate limiting counters
- Celery task queue backend
- Plaid sync status cache

**Exports**:
- Redis endpoint
- Redis port
- Security group ID

---

### 6. DnsStack (Route53, ACM) - OPTIONAL
**Purpose**: DNS and SSL certificates
**Dependencies**: None (optional stack - only created if domain configured)

**Important**: This stack is **completely optional**. The application works perfectly without a custom domain using ALB DNS names.

**When to Use**:
- ✅ You have a domain registered (Route53 or external registrar)
- ✅ You want custom URLs like `api.yourdomain.com`
- ✅ Production or staging environments
- ❌ Not needed for development (use ALB DNS)
- ❌ Not needed if you haven't chosen a domain yet

**Resources** (only if `domain_name` is set in cdk.context.json):
- Route53 hosted zone:
  - Creates hosted zone for your domain
  - Provides NS records to configure with registrar
  - Manages all DNS records for subdomains
- ACM certificates:
  - Wildcard certificate: `*.{domain}` (covers all subdomains)
  - DNS validation (automatic via Route53)
  - Auto-renewal enabled
- A Records for services:
  - `api.{domain}` → Backend API ALB
  - `app.{domain}` → Frontend ALB
  - `grafana.{domain}` → Grafana monitoring UI
  - `prometheus.{domain}` → Prometheus (optional, internal use)

**Subdomain Strategy**:
- **Development**: No custom domain (use ALB DNS names)
  - Backend: `dev-backend-1234567890.us-east-1.elb.amazonaws.com`
  - Frontend: `dev-frontend-0987654321.us-east-1.elb.amazonaws.com`
- **Staging**: Environment-prefixed subdomains
  - `api-staging.yourdomain.com`
  - `app-staging.yourdomain.com`
  - `grafana-staging.yourdomain.com`
- **Production**: Clean subdomains
  - `api.yourdomain.com`
  - `app.yourdomain.com`
  - `grafana.yourdomain.com`

**Configuration in cdk.context.json**:
```json
{
  "development": {
    "domain_name": null  // No domain for dev
  },
  "staging": {
    "domain_name": "yourdomain.com"  // Optional
  },
  "production": {
    "domain_name": "yourdomain.com"  // Set when ready
  }
}
```

**First-Time Domain Setup** (when you get a domain):
1. Set `domain_name` in cdk.context.json for desired environment
2. Deploy DnsStack: `make deploy-dns ENV=production`
3. Get NS records: `aws route53 list-hosted-zones-by-name --dns-name yourdomain.com`
4. Configure NS records with your domain registrar
5. Wait 5-10 minutes for DNS propagation
6. Certificate will auto-validate via DNS
7. Deploy/update ComputeStack to use certificate

**Exports**:
- Hosted zone ID
- Certificate ARN
- Subdomain names (api, app, grafana)

---

### 7. ComputeStack (ECS Fargate)
**Purpose**: Container orchestration for all services
**Dependencies**: SecurityStack, DatabaseStack, CacheStack, EcrStack, StorageStack, DnsStack (optional)

**Resources**:

#### ECS Cluster
- Fargate cluster with Container Insights enabled
- CloudMap namespace for service discovery

#### Backend Service (FastAPI)
- Task definition:
  - Development: 0.5 vCPU, 1GB RAM
  - Staging: 1 vCPU, 2GB RAM
  - Production: 2 vCPU, 4GB RAM
- Environment variables:
  - DATABASE_URL (from Secrets Manager)
  - REDIS_URL
  - PLAID_CLIENT_ID (from Secrets Manager)
  - PLAID_SECRET (from Secrets Manager)
  - JWT_SECRET (from Secrets Manager)
- Auto-scaling:
  - Min tasks: 1 (dev), 2 (staging), 2 (prod)
  - Max tasks: 4 (dev), 10 (staging), 20 (prod)
  - CPU target: 70%
- Health check: `/health`
- Application Load Balancer
  - HTTPS listener (if DNS configured)
  - HTTP → HTTPS redirect
  - Target group health checks

#### Frontend Service (Next.js)
- Task definition:
  - Development: 0.5 vCPU, 1GB RAM
  - Staging: 1 vCPU, 2GB RAM
  - Production: 1 vCPU, 2GB RAM
- Environment variables:
  - NEXT_PUBLIC_API_URL
- Auto-scaling:
  - Min tasks: 1 (dev), 2 (staging), 2 (prod)
  - Max tasks: 4 (dev), 6 (staging), 10 (prod)
- Health check: `/api/health`
- Application Load Balancer (separate from backend)

#### Worker Service (Celery)
- Task definition:
  - Development: 0.5 vCPU, 1GB RAM
  - Staging: 1 vCPU, 2GB RAM
  - Production: 1 vCPU, 2GB RAM
- Environment variables: Same as backend
- Task count:
  - Development: 1
  - Staging: 2
  - Production: 3
- No load balancer (internal service)

#### Migration Job (Alembic)
- Run-once task for database migrations
- Executed before service deployments
- Uses same image as backend
- Command override: `alembic upgrade head`

**Service Discovery**:
- CloudMap private namespace: `{env}.family-budget.local`
- Services:
  - `backend.{env}.family-budget.local`
  - `worker.{env}.family-budget.local`

**Exports**:
- Cluster ARN
- Service ARNs
- Load balancer DNS names
- Target group ARNs

---

### 8. NotificationStack (SES, SNS)
**Purpose**: Email and push notifications
**Dependencies**: SecurityStack

**Resources**:

#### SES (Email)
- Verified domain (if DNS configured)
- Configuration set with event tracking
- Development: Sandbox mode
- Production: Production access (requires AWS support request)
- Bounce and complaint handling

#### SNS Topics
- `{env}-bill-reminders` - Bill due notifications
- `{env}-budget-alerts` - Budget threshold alerts
- `{env}-account-sync-failures` - Plaid sync issues
- `{env}-security-alerts` - Suspicious activity

#### SNS Platform Application (Push Notifications)
- APNs for iOS (production and sandbox)
- FCM for Android

**Lambda Functions**:
- Email template renderer
- Push notification formatter
- Notification preference filter

**Exports**:
- SES configuration set name
- SNS topic ARNs
- Lambda function ARNs

---

### 9. MonitoringStack (Prometheus + Grafana)
**Purpose**: Cost-effective observability and alerting
**Dependencies**: ComputeStack, DatabaseStack, CacheStack, DnsStack (optional)

**Cost Strategy**: Use Prometheus + Grafana for metrics/dashboards instead of CloudWatch to minimize costs. Only use CloudWatch for critical alarms.

**Resources**:

#### EFS File System
- Persistent storage for Prometheus time-series data and Grafana config
- Performance mode: General Purpose
- Throughput mode: Bursting
- Lifecycle management:
  - Development: Delete on stack destroy
  - Production: Retain on stack destroy (manual cleanup)
- Automatic backups enabled (production only)
- Access points:
  - `/prometheus` - uid:gid 65534:65534 (nobody user)
  - `/grafana` - uid:gid 472:472 (Grafana default user)
- Mounted in ECS tasks in private subnets

#### Prometheus ECS Service
- **Image**: `prom/prometheus:latest`
- **Task definition**:
  - Development: 0.5 vCPU, 1GB RAM
  - Staging: 0.5 vCPU, 1GB RAM
  - Production: 1 vCPU, 2GB RAM
- **Configuration** (stored in SSM Parameter Store):
  - Scrape interval: 15s
  - Evaluation interval: 15s
  - Data retention: 15 days
  - Service discovery via CloudMap
- **Scraping targets** (via DNS service discovery):
  - `backend.{env}.family-budget.local:8000/metrics`
  - `frontend.{env}.family-budget.local:3000/metrics`
  - `worker.{env}.family-budget.local:8000/metrics`
  - `postgres-exporter.{env}.family-budget.local:9187/metrics`
  - `redis-exporter.{env}.family-budget.local:9121/metrics`
- **Task count**: 1 (not auto-scaled)
- **Access**:
  - Internal via CloudMap: `prometheus.{env}.family-budget.local:9090`
  - External via ALB: `prometheus.{domain}` (if domain configured)
  - Fallback: ALB DNS name

#### Grafana ECS Service
- **Image**: `grafana/grafana:latest`
- **Task definition**:
  - Development: 0.5 vCPU, 1GB RAM
  - Staging: 0.5 vCPU, 1GB RAM
  - Production: 1 vCPU, 2GB RAM
- **Configuration** (provisioned via SSM Parameter Store):
  - Datasource: Prometheus (pre-configured)
  - Admin credentials: Stored in Secrets Manager
  - Anonymous auth: Disabled
  - Allow embedding: Enabled (for mobile app)
- **Pre-provisioned Dashboards**:
  1. **Application Overview**
     - Request rate, latency (p50, p95, p99)
     - Error rate (4xx, 5xx)
     - Active users
  2. **ECS Services Health**
     - CPU and memory utilization
     - Task count and restarts
     - Network I/O
  3. **Database Performance**
     - Active connections
     - Query performance
     - Cache hit ratio
     - Transaction rate
     - Replication lag (if Multi-AZ)
  4. **Redis Performance**
     - Memory usage
     - Commands/sec
     - Key evictions
     - Hit/miss ratio
  5. **Plaid Integration**
     - Sync success/failure rate
     - API call latency
     - Webhook delivery
  6. **Business Metrics**
     - Bill reminders sent
     - Budget alerts triggered
     - User sign-ups
     - Active households
- **Task count**: 1 (not auto-scaled)
- **Access**:
  - Internal via CloudMap: `grafana.{env}.family-budget.local:3000`
  - External via ALB: `grafana.{domain}` (if domain configured)
  - Fallback: ALB DNS name

#### Metric Exporters (Sidecar Containers)

**Postgres Exporter** (added to backend task):
- Image: `quay.io/prometheuscommunity/postgres-exporter:latest`
- Connects to RDS via connection string from Secrets Manager
- Port: 9187
- Exported metrics:
  - pg_stat_database (connections, transactions, conflicts)
  - pg_stat_activity (active queries)
  - pg_locks (lock counts)
  - pg_replication (replication lag if Multi-AZ)

**Redis Exporter** (added to worker task):
- Image: `oliver006/redis_exporter:latest`
- Connects to ElastiCache endpoint
- Port: 9121
- Exported metrics:
  - redis_memory_used_bytes
  - redis_connected_clients
  - redis_commands_processed_total
  - redis_keyspace_hits/misses

#### Monitoring ALB
- Application Load Balancer for Grafana/Prometheus access
- Listeners:
  - HTTPS:443 (if certificate available) → forward to Grafana
  - HTTP:80 → redirect to HTTPS or forward (no cert)
- Target groups:
  - Grafana target group (health check: `/api/health`)
  - Prometheus target group (health check: `/-/healthy`)
- Security group: Allow inbound 443/80 from internet (or VPN if preferred)
- Route53 A records (if domain configured)

#### SNS Topic (Critical Alarms Only)
- **Purpose**: Only for absolutely critical issues requiring immediate action
- **Email subscription**: From cdk.context.json `alarm_email`
- **Connected to CloudWatch Alarms**:

  **CRITICAL (all environments)**:
  - All ECS tasks down (backend, frontend, worker)
  - Database storage < 5GB
  - Database CPU > 95% for 15 minutes

  **Production only**:
  - High sustained error rate (5xx > 50% for 10 min)
  - Database connection exhaustion (> 90% for 5 min)
  - ALB unhealthy targets for > 5 minutes

#### SSM Parameters
- `/{env}/monitoring/prometheus-config` - Prometheus scrape configuration (YAML)
- `/{env}/monitoring/grafana/datasource` - Grafana datasource provisioning (YAML)
- `/{env}/monitoring/grafana/dashboard` - Grafana dashboard provisioning (YAML)

#### Security Group
- Allows Grafana and Prometheus to communicate
- Allows Prometheus to scrape all services in VPC
- Allows inbound from ALB to Grafana/Prometheus
- Allows EFS access for persistent storage

---

**CloudWatch Usage** (Minimal - Cost Optimization):
- ❌ **No custom CloudWatch dashboards** (use Grafana instead)
- ❌ **No detailed CloudWatch metrics** (Prometheus collects all metrics)
- ❌ **No custom log groups** (use ECS default logging only)
- ❌ **No log retention > 3 days** (except RDS logs: 7 days)
- ❌ **No CloudWatch Logs Insights queries** (use Grafana/Loki if needed later)
- ✅ **Only critical CloudWatch alarms** (< 5 alarms total)
- ✅ **Basic ECS/ALB/RDS metrics** (included by default, no extra cost)
- ✅ **ECS awslogs driver** (default, minimal cost with short retention)

**Cost Savings**:
- CloudWatch dashboards: $3/dashboard/month → **$0** (using Grafana)
- CloudWatch custom metrics: $0.30 per metric → **$0** (using Prometheus)
- CloudWatch Logs: $0.50/GB ingested → **~$0.05/month** (3-day retention only)
- Total savings: **~$10-20/month** vs. full CloudWatch setup

**Exports**:
- Grafana URL (ALB DNS or custom domain)
- Prometheus URL (ALB DNS or custom domain)
- Grafana admin credentials secret ARN
- SNS alarm topic ARN

---

## Stack Dependencies

```
┌─────────────────┐
│  SecurityStack  │ (VPC, Secrets, KMS)
└────────┬────────┘
         │
    ┌────┴────────────────────┬──────────────┬──────────────┐
    │                         │              │              │
    ▼                         ▼              ▼              ▼
┌───────────┐          ┌──────────────┐  ┌─────────┐  ┌─────────┐
│ Database  │          │    Cache     │  │ DnsStack│  │ Storage │
│   Stack   │          │    Stack     │  │         │  │  Stack  │
└─────┬─────┘          └──────┬───────┘  └────┬────┘  └────┬────┘
      │                       │               │            │
      └───────┬───────────────┴───────────────┴────────────┘
              │
    ┌─────────┴─────────┐
    │   ComputeStack    │ (ECS Services)
    │  + Notification   │
    └─────────┬─────────┘
              │
              ▼
    ┌─────────────────┐
    │ MonitoringStack │
    └─────────────────┘
```

**Deployment Order**:
1. SecurityStack
2. EcrStack, StorageStack, DnsStack (parallel)
3. DatabaseStack, CacheStack (parallel, after Security)
4. NotificationStack (after Security)
5. ComputeStack (after all dependencies)
6. MonitoringStack (after Compute)

---

## Configuration Files

### cdk.json
```json
{
  "app": "python3 app.py",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "**/__pycache__",
      "**/*.pyc"
    ]
  },
  "context": {
    "@aws-cdk/core:enableStackNameDuplicates": "true",
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true,
    "@aws-cdk/core:stackRelativeExports": "true",
    "@aws-cdk/aws-rds:lowercaseDbIdentifier": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true
  }
}
```

### cdk.context.json (example - actual file is gitignored)
```json
{
  "development": {
    "account": "123456789012",
    "region": "us-east-1",
    "domain_name": null,
    "alarm_email": null,
    "plaid_environment": "sandbox"
  },
  "staging": {
    "account": "123456789012",
    "region": "us-east-1",
    "domain_name": "familybudget.app",
    "alarm_email": "alerts@example.com",
    "plaid_environment": "development"
  },
  "production": {
    "account": "987654321098",
    "region": "us-east-1",
    "domain_name": "familybudget.app",
    "alarm_email": "alerts@example.com",
    "plaid_environment": "production"
  }
}
```

### requirements.txt
```txt
aws-cdk-lib==2.115.0
constructs>=10.0.0,<11.0.0
```

---

## Makefile

```makefile
.PHONY: help install synth diff deploy destroy clean

ENV ?= development

help:
    @echo "Family Budget App - Infrastructure Management"
    @echo ""
    @echo "Available commands:"
    @echo "  make install          - Install CDK dependencies"
    @echo "  make synth            - Synthesize CloudFormation templates"
    @echo "  make diff             - Show infrastructure changes"
    @echo "  make deploy           - Deploy all stacks"
    @echo "  make deploy-stack     - Deploy specific stack (STACK=name)"
    @echo "  make destroy          - Destroy all stacks"
    @echo "  make clean            - Clean CDK artifacts"
    @echo "  make bootstrap        - Bootstrap CDK (first time setup)"
    @echo ""
    @echo "Individual stack deployments:"
    @echo "  make deploy-security       - Deploy SecurityStack"
    @echo "  make deploy-database       - Deploy DatabaseStack"
    @echo "  make deploy-cache          - Deploy CacheStack"
    @echo "  make deploy-storage        - Deploy StorageStack"
    @echo "  make deploy-ecr            - Deploy EcrStack"
    @echo "  make deploy-dns            - Deploy DnsStack"
    @echo "  make deploy-compute        - Deploy ComputeStack"
    @echo "  make deploy-notification   - Deploy NotificationStack"
    @echo "  make deploy-monitoring     - Deploy MonitoringStack"
    @echo ""
    @echo "Environment-specific:"
    @echo "  make deploy-dev       - Deploy development environment"
    @echo "  make deploy-staging   - Deploy staging environment"
    @echo "  make deploy-prod      - Deploy production environment"
    @echo ""
    @echo "Environment: $(ENV) (set ENV=development|staging|production)"

install:
    pip install -r requirements.txt

synth:
    cdk synth -c environment=$(ENV)

diff:
    cdk diff -c environment=$(ENV) --all

deploy:
    cdk deploy --all -c environment=$(ENV) --require-approval never

deploy-stack:
    cdk deploy $(ENV)-$(STACK)Stack -c environment=$(ENV)

destroy:
    cdk destroy --all -c environment=$(ENV)

clean:
    rm -rf cdk.out
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete

bootstrap:
    @echo "Bootstrapping CDK for environment: $(ENV)"
    @echo "Make sure you have AWS credentials configured"
    cdk bootstrap -c environment=$(ENV)

# Individual stack deployments
deploy-security:
    $(MAKE) deploy-stack STACK=Security

deploy-database:
    $(MAKE) deploy-stack STACK=Database

deploy-cache:
    $(MAKE) deploy-stack STACK=Cache

deploy-storage:
    $(MAKE) deploy-stack STACK=Storage

deploy-ecr:
    $(MAKE) deploy-stack STACK=Ecr

deploy-dns:
    $(MAKE) deploy-stack STACK=Dns

deploy-compute:
    $(MAKE) deploy-stack STACK=Compute

deploy-notification:
    $(MAKE) deploy-stack STACK=Notification

deploy-monitoring:
    $(MAKE) deploy-stack STACK=Monitoring

# Environment-specific deployments
deploy-dev:
    $(MAKE) deploy ENV=development

deploy-staging:
    $(MAKE) deploy ENV=staging

deploy-prod:
    $(MAKE) deploy ENV=production

# Utility commands
list-stacks:
    cdk list -c environment=$(ENV)

watch:
    cdk watch -c environment=$(ENV)
```

---

## app.py Structure

```python
#!/usr/bin/env python3
"""CDK app for Family Budget infrastructure"""

import os
import aws_cdk as cdk
from stacks.security_stack import SecurityStack
from stacks.ecr_stack import EcrStack
from stacks.storage_stack import StorageStack
from stacks.database_stack import DatabaseStack
from stacks.cache_stack import CacheStack
from stacks.dns_stack import DnsStack
from stacks.compute_stack import ComputeStack
from stacks.notification_stack import NotificationStack
from stacks.monitoring_stack import MonitoringStack

# Initialize app
app = cdk.App()

# Get configuration
environment = app.node.try_get_context("environment") or os.environ.get("ENVIRONMENT", "development")
account = app.node.try_get_context("account") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

# Load environment-specific config
env_config = app.node.try_get_context(environment) or {}
alarm_email = env_config.get("alarm_email")
domain_name = env_config.get("domain_name")
plaid_environment = env_config.get("plaid_environment", "sandbox")

# Validate configuration
if not account:
    raise ValueError("AWS account ID required. Set CDK_DEFAULT_ACCOUNT or run 'cdk bootstrap'")

# Create AWS environment
env = cdk.Environment(account=account, region=region)

# Apply tags
cdk.Tags.of(app).add("Project", "FamilyBudget")
cdk.Tags.of(app).add("Environment", environment)
cdk.Tags.of(app).add("ManagedBy", "CDK")

print(f"🚀 Deploying Family Budget infrastructure for {environment}")
print(f"📍 Region: {region}")
print(f"🔑 Account: {account}")
print(f"💳 Plaid: {plaid_environment}")
print("")

# 1. Security Stack
security_stack = SecurityStack(
    app, f"{environment}-SecurityStack",
    env_name=environment,
    env=env,
    description=f"Security resources (VPC, Secrets) for {environment}"
)

# 2. ECR Stack (parallel)
ecr_stack = EcrStack(
    app, f"{environment}-EcrStack",
    env_name=environment,
    env=env,
    description=f"Container registries for {environment}"
)

# 3. Storage Stack (parallel)
storage_stack = StorageStack(
    app, f"{environment}-StorageStack",
    env_name=environment,
    env=env,
    description=f"S3 buckets for {environment}"
)

# 4. Database Stack
database_stack = DatabaseStack(
    app, f"{environment}-DatabaseStack",
    vpc=security_stack.vpc,
    env_name=environment,
    env=env,
    description=f"RDS PostgreSQL for {environment}"
)
database_stack.add_dependency(security_stack)

# 5. Cache Stack
cache_stack = CacheStack(
    app, f"{environment}-CacheStack",
    vpc=security_stack.vpc,
    env_name=environment,
    env=env,
    description=f"ElastiCache Redis for {environment}"
)
cache_stack.add_dependency(security_stack)

# 6. DNS Stack (optional)
dns_stack = None
if domain_name:
    dns_stack = DnsStack(
        app, f"{environment}-DnsStack",
        env_name=environment,
        domain_name=domain_name,
        env=env,
        description=f"DNS and SSL for {environment}"
    )

# 7. Notification Stack
notification_stack = NotificationStack(
    app, f"{environment}-NotificationStack",
    vpc=security_stack.vpc,
    env_name=environment,
    env=env,
    description=f"SES and SNS for {environment}"
)
notification_stack.add_dependency(security_stack)

# 8. Compute Stack
compute_stack = ComputeStack(
    app, f"{environment}-ComputeStack",
    vpc=security_stack.vpc,
    database_secret=database_stack.database_secret,
    plaid_secret=security_stack.plaid_secret,
    jwt_secret=security_stack.jwt_secret,
    database_security_group=database_stack.security_group,
    cache_security_group=cache_stack.security_group,
    redis_endpoint=cache_stack.redis_endpoint,
    redis_port=cache_stack.redis_port,
    exports_bucket=storage_stack.exports_bucket,
    receipts_bucket=storage_stack.receipts_bucket,
    env_name=environment,
    plaid_environment=plaid_environment,
    certificate=dns_stack.certificate if dns_stack else None,
    hosted_zone=dns_stack.hosted_zone if dns_stack else None,
    env=env,
    description=f"ECS services for {environment}"
)
compute_stack.add_dependency(security_stack)
compute_stack.add_dependency(database_stack)
compute_stack.add_dependency(cache_stack)
compute_stack.add_dependency(ecr_stack)
compute_stack.add_dependency(storage_stack)
if dns_stack:
    compute_stack.add_dependency(dns_stack)

# 9. Monitoring Stack
monitoring_stack = MonitoringStack(
    app, f"{environment}-MonitoringStack",
    cluster=compute_stack.cluster,
    backend_service=compute_stack.backend_service,
    frontend_service=compute_stack.frontend_service,
    worker_service=compute_stack.worker_service,
    database=database_stack.database,
    cache_cluster=cache_stack.cache_cluster,
    backend_target_group=compute_stack.backend_target_group,
    frontend_target_group=compute_stack.frontend_target_group,
    env_name=environment,
    alarm_email=alarm_email,
    env=env,
    description=f"Monitoring and alarms for {environment}"
)
monitoring_stack.add_dependency(compute_stack)
monitoring_stack.add_dependency(database_stack)
monitoring_stack.add_dependency(cache_stack)

app.synth()

print("✅ CDK synthesis complete!")
```

---

## Secrets Management

All secrets are managed via AWS Secrets Manager and populated using `scripts/populate-secrets.py`.

### Required Secrets

1. **Database Credentials** - `{env}/family-budget/database`
   ```json
   {
     "username": "dbadmin",
     "password": "<generated>",
     "engine": "postgres",
     "host": "<rds-endpoint>",
     "port": 5432,
     "dbname": "family_budget"
   }
   ```

2. **Plaid API Keys** - `{env}/family-budget/plaid`
   ```json
   {
     "client_id": "<plaid-client-id>",
     "secret": "<plaid-secret>",
     "environment": "sandbox|development|production"
   }
   ```

3. **JWT Configuration** - `{env}/family-budget/jwt`
   ```json
   {
     "secret_key": "<generated-256-bit-key>",
     "algorithm": "HS256",
     "access_token_expire_minutes": 15,
     "refresh_token_expire_days": 7
   }
   ```

4. **External Services** - `{env}/family-budget/external-services`
   ```json
   {
     "sendgrid_api_key": "<optional>",
     "sentry_dsn": "<optional>",
     "stripe_api_key": "<optional-for-future>"
   }
   ```

---

## Cost Optimization Strategies

### Development Environment
- Single NAT Gateway
- Smallest instance sizes
- No Multi-AZ
- 7-day backup retention
- No VPC Flow Logs
- No KMS encryption (use AWS managed keys)

### Staging Environment
- Single NAT Gateway (acceptable risk)
- Medium instance sizes
- No Multi-AZ (acceptable risk)
- 14-day backup retention
- VPC Flow Logs enabled
- CloudWatch log retention: 14 days

### Production Environment
- Dual NAT Gateways (HA)
- Right-sized instances with auto-scaling
- Multi-AZ for RDS
- 30-day backup retention
- VPC Flow Logs with S3 export
- CloudWatch log retention: 90 days
- KMS encryption for sensitive data
- CloudFront CDN for static assets

---

## Deployment Guide

### First-Time Setup

1. **Install dependencies**:
   ```bash
   cd infrastructure
   make install
   ```

2. **Configure AWS credentials**:
   ```bash
   aws configure
   # Or use AWS_PROFILE environment variable
   ```

3. **Update cdk.context.json** with your account/region

4. **Bootstrap CDK**:
   ```bash
   make bootstrap ENV=development
   ```

5. **Populate secrets**:
   ```bash
   python scripts/populate-secrets.py --environment development
   ```

6. **Deploy infrastructure**:
   ```bash
   make deploy-dev
   ```

### Updating Infrastructure

1. **Review changes**:
   ```bash
   make diff ENV=staging
   ```

2. **Deploy specific stack**:
   ```bash
   make deploy-database ENV=staging
   ```

3. **Deploy all stacks**:
   ```bash
   make deploy-staging
   ```

### Monitoring Deployments

- Check CloudFormation console for stack status
- Review CloudWatch logs for ECS task startup
- Verify ALB target health in EC2 console
- Test endpoints with curl/Postman

---

## Troubleshooting

### Common Issues

**Issue**: Stack deployment fails with "Exceeded maximum number of attempts"
- **Solution**: Check CloudWatch logs for ECS tasks, verify security group rules allow traffic

**Issue**: Database connection timeout from ECS
- **Solution**: Ensure ECS security group has ingress to RDS security group on port 5432

**Issue**: Certificate validation pending
- **Solution**: Add NS records from Route53 hosted zone to domain registrar, wait 5-10 minutes

**Issue**: Plaid API calls failing
- **Solution**: Verify secrets are populated correctly, check Plaid dashboard for API status

**Issue**: High NAT Gateway costs
- **Solution**: Consider VPC endpoints for AWS services (S3, ECR, Secrets Manager, SES)

---

## Security Best Practices

1. **Secrets Rotation**
   - Enable automatic rotation for RDS credentials (production)
   - Rotate JWT signing keys quarterly
   - Rotate Plaid API keys as needed

2. **IAM Least Privilege**
   - Task roles have minimal permissions
   - No wildcards in IAM policies
   - Use resource-specific grants

3. **Network Isolation**
   - RDS in isolated subnets (no internet access)
   - ECS tasks in private subnets
   - ALB in public subnets only

4. **Encryption**
   - Encryption in transit (TLS 1.3)
   - Encryption at rest (all storage)
   - KMS encryption for production secrets

5. **Monitoring & Alerts**
   - CloudWatch alarms for anomalies
   - VPC Flow Logs for network analysis
   - CloudTrail for API audit logging

---

## Future Enhancements

- [ ] AWS WAF for ALB (DDoS protection, rate limiting)
- [ ] CloudFront CDN for frontend (global performance)
- [ ] ElastiCache Redis Cluster mode (higher availability)
- [ ] RDS Read Replicas (scale read traffic)
- [ ] Multi-region deployment (disaster recovery)
- [ ] AWS Backup for centralized backup management
- [ ] Systems Manager Parameter Store integration
- [ ] CodePipeline for automated deployments
- [ ] Lambda@Edge for edge computing
- [ ] AWS AppSync for GraphQL API (alternative to FastAPI)

---

*This infrastructure plan is based on proven patterns from cipher-dnd-bot, adapted for the Family Budget application's specific requirements.*
