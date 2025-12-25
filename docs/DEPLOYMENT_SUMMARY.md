# Wumbo Deployment Infrastructure Summary

This document summarizes the complete infrastructure and CI/CD setup for the Wumbo application.

## Overview

Wumbo is deployed using AWS infrastructure with automated CI/CD pipelines for backend, web frontend, and mobile applications.

**Domain**: wumbo.app
**iOS Bundle ID**: com.built-by-dusty.wumbo
**Android Package ID**: com.built_by_dusty.wumbo

## Infrastructure Components

### 1. AWS CDK Stacks

All infrastructure is defined as code using AWS CDK (Python). Located in `/infrastructure`.

#### SecurityStack
- **VPC** with public, private, and isolated subnets
- **NAT Gateways** (1 for dev/staging, 2 for production)
- **VPC Endpoints** for ECR, Secrets Manager, CloudWatch, SES
- **Secrets Manager** for Plaid, AWS, and app credentials
- **KMS encryption** (production only)

#### EcrStack
- **Container registries** for backend and migration images
- **Lifecycle policies** to manage image retention
- **IAM user** for GitHub Actions ECR access

#### DatabaseStack
- **RDS PostgreSQL 16** with Graviton instances (cost optimized)
- **Multi-AZ** in production for high availability
- **Automated backups** with configurable retention
- **Performance Insights** (production only)
- Database: `wumbo`

#### CacheStack
- **ElastiCache Redis 7.1** for caching and Celery broker
- **Graviton instances** (t4g/r7g) for cost savings
- **Multi-AZ replication** in production
- **Encryption at rest and in transit** (production)

#### ComputeStack
- **ECS Fargate services**:
  - Backend API (FastAPI)
  - Celery Worker (background tasks)
  - Celery Beat (task scheduler)
- **Application Load Balancer** for backend API
- **Service discovery** via AWS Cloud Map
- **Auto-scaling** based on CPU/memory

#### MonitoringStack
- **SNS topics** for CloudWatch alarms
- **Email notifications** (configurable)
- **Placeholder for Prometheus/Grafana** (future enhancement)

### 2. Environment Configuration

Three environments are supported:

| Environment | Branch | Purpose |
|-------------|--------|---------|
| development | develop | Development and testing |
| staging | N/A | Pre-production validation |
| production | main | Live application |

### 3. Cost Estimates

**Development** (~$90-100/month):
- NAT Gateway: $32
- RDS t4g.micro: $12
- ElastiCache t4g.micro: $12
- ECS Fargate (3 tasks): $30-40

**Production** (~$320-370/month):
- NAT Gateways (2): $64
- RDS t4g.small Multi-AZ: $50
- ElastiCache r7g.large: $106
- ECS Fargate (6-10 tasks): $100-150

## CI/CD Pipelines

### Backend CI/CD (`.github/workflows/backend-deploy.yml`)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests (test only)

**Pipeline**:
1. **Test** - Run linting and tests
2. **Build** - Build Docker image and push to ECR
3. **Deploy** - Update ECS services (backend, worker, beat)

**Services Updated**:
- `{env}-wumbo-backend`
- `{env}-wumbo-worker`
- `{env}-wumbo-beat`

**Required Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Frontend CI/CD (`.github/workflows/frontend-deploy.yml`)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests (test only)

**Pipeline**:
1. **Test** - Linting and type checking
2. **Build** - Next.js build
3. **Deploy** - AWS Amplify (primary) or S3 + CloudFront (alternative)

**Required Secrets**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AMPLIFY_APP_ID` (if using Amplify)
- `CLOUDFRONT_DISTRIBUTION_ID` (if using S3/CloudFront)
- `NEXT_PUBLIC_API_URL`

### Mobile CI/CD (`.github/workflows/mobile-build.yml`)

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests (test only)
- Manual workflow dispatch

**Pipeline**:
1. **Test** - Linting and type checking
2. **Build** - EAS Build for iOS and Android
3. **Submit** - App store submission (production only)
4. **OTA Update** - Publish EAS Update (non-production)

**Build Profiles**:
- **development**: Development builds with simulator support
- **preview**: Beta testing builds (TestFlight/Internal Testing)
- **production**: Production builds for app stores

**Required Secrets**:
- `EXPO_TOKEN`
- `EXPO_PUBLIC_API_URL`
- Apple credentials (for iOS submission)
- Google service account (for Android submission)

## Deployment Process

### Initial Setup

1. **Install CDK and dependencies**
   ```bash
   cd infrastructure
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Bootstrap AWS account**
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/us-east-1
   ```

3. **Create secrets in AWS Secrets Manager**
   ```bash
   # Plaid credentials
   aws secretsmanager create-secret \
     --name development/wumbo/plaid \
     --secret-string '{"client_id":"...","secret":"...","environment":"sandbox"}'

   # AWS credentials (for SES)
   aws secretsmanager create-secret \
     --name development/wumbo/aws \
     --secret-string '{"access_key_id":"...","secret_access_key":"...","region":"us-east-1"}'

   # App security
   aws secretsmanager create-secret \
     --name development/wumbo/app-security \
     --secret-string '{"jwt_secret_key":"...","algorithm":"HS256"}'
   ```

4. **Deploy infrastructure**
   ```bash
   cd infrastructure
   make deploy ENV=development
   ```

5. **Configure GitHub secrets**
   - Add AWS credentials
   - Add Expo token
   - Add API URLs
   - Add app store credentials

### Updating Services

**Backend**:
- Push to `develop` or `main` branch
- GitHub Actions automatically builds and deploys

**Frontend**:
- Push to `develop` or `main` branch
- Amplify automatically deploys

**Mobile**:
- Push triggers EAS build
- Manual workflow dispatch for specific builds
- Use EAS Update for JavaScript-only changes

## Security

### Secrets Management
- All secrets stored in AWS Secrets Manager
- Encrypted at rest with KMS (production)
- Accessed via IAM roles (no hardcoded credentials)

### Network Security
- Private subnets for compute resources
- Isolated subnets for databases
- Security groups restrict traffic
- No public database access

### Application Security
- JWT authentication with refresh tokens
- Plaid access tokens (encryption pending)
- HTTPS-only communication
- CORS configured for web app

## Monitoring and Logging

### CloudWatch Logs
- Backend API logs: `/aws/ecs/{env}-wumbo-backend`
- Worker logs: `/aws/ecs/{env}-wumbo-worker`
- Beat logs: `/aws/ecs/{env}-wumbo-beat`

### Metrics
- Container Insights (production only)
- RDS Performance Insights (production only)
- Custom application metrics via Prometheus (planned)

### Alarms
- SNS topic: `{env}-family-budget-alarms`
- Email notifications (configurable)

## Database Migrations

Run Alembic migrations:

```bash
# From backend container or locally
cd backend
alembic upgrade head
```

**TODO**: Add migration task definition for automated migrations via ECS.

## Mobile App Configuration

### EAS Build Profiles

Located in `apps/mobile/eas.json`:

- **development**: Dev builds with simulator support
- **preview**: Internal testing builds
- **production**: App store builds

### App Identifiers

**iOS**:
- Development: `com.built-by-dusty.wumbo.dev`
- Staging: `com.built-by-dusty.wumbo.staging`
- Production: `com.built-by-dusty.wumbo`

**Android**:
- Development: `com.built_by_dusty.wumbo.dev`
- Staging: `com.built_by_dusty.wumbo.staging`
- Production: `com.built_by_dusty.wumbo`

### API URLs

- Development: `https://dev-api.wumbo.app`
- Staging: `https://staging-api.wumbo.app`
- Production: `https://api.wumbo.app`

## Next Steps

### Immediate
1. **Get Plaid credentials** - Sign up at plaid.com and get sandbox credentials
2. **Configure AWS SES** - Verify email domain for sending emails
3. **Set up Expo account** - Create organization and get access token
4. **Deploy development stack** - Test infrastructure deployment

### Short-term
1. **SSL/TLS certificates** - Add ACM certificates for HTTPS
2. **Custom domain** - Configure Route53 and DNS
3. **Database encryption** - Add Fernet encryption for Plaid tokens
4. **Webhook verification** - Verify Plaid webhook signatures

### Medium-term
1. **Prometheus/Grafana** - Complete monitoring stack implementation
2. **Automated migrations** - ECS task for running Alembic migrations
3. **App store setup** - Create apps in App Store Connect and Google Play Console
4. **Beta testing** - TestFlight and Google Play Internal Testing

### Long-term
1. **WAF** - Web Application Firewall for production
2. **CloudFront** - CDN for frontend assets
3. **Backup strategy** - Automated database backups and restore testing
4. **Disaster recovery** - Multi-region failover plan

## Troubleshooting

### Common Issues

**ECS tasks failing to start**:
- Check CloudWatch Logs for error messages
- Verify secrets exist in Secrets Manager
- Ensure security groups allow database/Redis access

**Database connection errors**:
- Check security group ingress rules
- Verify RDS instance is in AVAILABLE state
- Check database credentials in secret

**GitHub Actions failures**:
- Verify AWS credentials in GitHub secrets
- Check ECR repository exists
- Ensure ECS cluster and services are created

### Getting Help

- **Infrastructure docs**: `infrastructure/README.md`
- **Backend docs**: `backend/README.md`
- **Mobile CI/CD**: `docs/MOBILE_CICD.md`
- **Brand guidelines**: `docs/BRAND_GUIDELINES.md`

## Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Plaid Documentation](https://plaid.com/docs/)
- [EAS Build Documentation](https://docs.expo.dev/build/introduction/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

**Version**: 1.0
**Last Updated**: December 2024
**Maintained By**: Built by Dusty
