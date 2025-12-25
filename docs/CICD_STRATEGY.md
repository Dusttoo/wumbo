# Wumbo App - CI/CD Strategy

This document outlines the comprehensive CI/CD pipeline strategy for the Wumbo application.

## Overview

**Goal**: Automated, reliable, and fast deployments with high confidence through comprehensive testing and quality checks.

**Architecture**: Multi-workflow GitHub Actions setup for monorepo with:
- Backend (FastAPI)
- Web frontend (Next.js)
- Mobile app (React Native/Expo)
- Shared UI library
- Infrastructure (AWS CDK)
- Database migrations

**Key Principles**:
1. **Path-based filtering** - Only build/test what changed
2. **Parallel execution** - Run independent jobs concurrently
3. **Environment isolation** - Separate dev/staging/production
4. **Security-first** - Scanning, secrets management, SBOM
5. **Fast feedback** - Fail fast on quality issues
6. **Automatic deployments** - Push to deploy (after tests pass)

---

## Workflow Structure

### 1. Main CI/CD Workflow (`deploy.yml`)

**Triggers**:
- Push to `main` branch → Deploy to production
- Push to `development` branch → Deploy to development
- Push to `staging` branch → Deploy to staging
- Pull requests → Run tests only (no deployment)
- Manual workflow dispatch → Deploy to chosen environment

**Jobs**:
1. **Code Quality & Tests**
   - Python (backend, worker)
   - TypeScript (web, mobile, shared UI)
   - Linting, formatting, type checking
   - Unit tests with coverage
2. **Change Detection**
   - Path filtering to determine what changed
   - Optimize build/deploy based on changes
3. **Build & Push Docker Images**
   - Backend (FastAPI)
   - Frontend (Next.js)
   - Worker (Celery)
   - Migrations runner
4. **Deploy Infrastructure** (if changed)
   - CDK diff
   - Deploy infrastructure stacks
5. **Run Database Migrations** (if changed)
   - Execute Alembic migrations
6. **Deploy Services**
   - Update ECS services with new images
   - Wait for services to stabilize
7. **Post-Deployment Validation**
   - Health checks
   - Smoke tests
8. **Notifications**
   - Success/failure alerts

### 2. Mobile App Workflow (`mobile.yml`)

**Triggers**:
- Push to `main` → Build production app
- Push to `development` → Build development app
- Manual dispatch → Build for specific environment

**Jobs**:
1. **Quality Checks**
   - TypeScript type checking
   - ESLint
   - Jest tests
2. **Build iOS App** (EAS Build)
   - Development build
   - Production build (main branch only)
3. **Build Android App** (EAS Build)
   - Development build
   - Production build (main branch only)
4. **Submit to Stores** (manual trigger only)
   - App Store (iOS)
   - Play Store (Android)

### 3. Pull Request Workflow (`pr.yml`)

**Triggers**:
- Pull request opened/updated

**Jobs**:
1. **Quality Gates**
   - All linting and formatting checks
   - Type checking
   - Unit tests
   - Integration tests
2. **Security Scanning**
   - Dependency vulnerability scanning
   - SAST (Static Application Security Testing)
3. **Build Verification**
   - Ensure all packages build successfully
   - Docker images build without errors
4. **E2E Tests** (optional, on label)
   - Run full E2E test suite
5. **Preview Deployment** (optional, on label)
   - Deploy to ephemeral environment
   - Comment PR with preview URLs

### 4. Security Workflow (`security.yml`)

**Triggers**:
- Schedule (daily)
- Manual dispatch

**Jobs**:
1. **Dependency Scanning**
   - npm audit (frontend packages)
   - pip-audit (backend)
   - Dependabot alerts
2. **Secret Scanning**
   - GitGuardian or TruffleHog
3. **License Compliance**
   - Check for incompatible licenses
4. **SBOM Generation**
   - Software Bill of Materials
5. **Container Scanning**
   - Scan Docker images for vulnerabilities

### 5. Infrastructure Workflow (`infrastructure.yml`)

**Triggers**:
- Changes to `infrastructure/**`
- Manual dispatch

**Jobs**:
1. **CDK Validation**
   - CDK synth
   - CDK diff
   - CloudFormation template validation
2. **Security Checks**
   - cfn-lint
   - checkov (IaC security)
3. **Cost Estimation**
   - Infracost (estimate infrastructure costs)
4. **Deploy** (on merge to main/development)
   - Deploy infrastructure changes
   - Update outputs

---

## Detailed Job Specifications

### Quality Checks (Backend)

```yaml
backend-quality:
  name: Backend Quality & Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Format check (Ruff)
      run: |
        cd backend
        ruff format --check .

    - name: Lint (Ruff)
      run: |
        cd backend
        ruff check .

    - name: Type check (MyPy)
      run: |
        cd backend
        mypy app/ --strict

    - name: Security check (Bandit)
      run: |
        cd backend
        bandit -r app/

    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml --cov-report=term

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./backend/coverage.xml
        flags: backend
```

### Quality Checks (Frontend - Web)

```yaml
web-quality:
  name: Web Frontend Quality & Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci
      working-directory: apps/web

    - name: Type check
      run: npm run type-check
      working-directory: apps/web

    - name: Lint
      run: npm run lint
      working-directory: apps/web

    - name: Format check
      run: npm run format:check
      working-directory: apps/web

    - name: Unit tests
      run: npm run test:ci
      working-directory: apps/web

    - name: Build
      run: npm run build
      working-directory: apps/web
```

### Quality Checks (Mobile)

```yaml
mobile-quality:
  name: Mobile App Quality & Tests
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'

    - name: Install dependencies
      run: npm ci
      working-directory: apps/mobile

    - name: Type check
      run: npm run type-check
      working-directory: apps/mobile

    - name: Lint
      run: npm run lint
      working-directory: apps/mobile

    - name: Unit tests
      run: npm run test:ci
      working-directory: apps/mobile
```

### Change Detection

```yaml
detect-changes:
  name: Detect Changed Files
  runs-on: ubuntu-latest
  outputs:
    backend: ${{ steps.changes.outputs.backend }}
    web: ${{ steps.changes.outputs.web }}
    mobile: ${{ steps.changes.outputs.mobile }}
    worker: ${{ steps.changes.outputs.worker }}
    ui: ${{ steps.changes.outputs.ui }}
    infrastructure: ${{ steps.changes.outputs.infrastructure }}
    migrations: ${{ steps.changes.outputs.migrations }}
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 2

    - name: Detect changes
      uses: dorny/paths-filter@v3
      id: changes
      with:
        filters: |
          backend:
            - 'backend/**'
          web:
            - 'apps/web/**'
          mobile:
            - 'apps/mobile/**'
          worker:
            - 'worker/**'
          ui:
            - 'packages/ui/**'
          infrastructure:
            - 'infrastructure/**'
            - '.github/workflows/**'
          migrations:
            - 'backend/alembic/**'
            - 'backend/app/models/**'
```

### Build & Push Docker Images

```yaml
build-and-push:
  name: Build & Push Docker Images
  needs: [backend-quality, web-quality, detect-changes, determine-environment]
  if: |
    github.event_name == 'push' &&
    (needs.detect-changes.outputs.backend == 'true' ||
     needs.detect-changes.outputs.web == 'true' ||
     needs.detect-changes.outputs.worker == 'true' ||
     needs.detect-changes.outputs.migrations == 'true')
  runs-on: ubuntu-latest
  environment: ${{ needs.determine-environment.outputs.environment }}

  steps:
    - uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION }}

    - name: Login to Amazon ECR
      uses: aws-actions/amazon-ecr-login@v2

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Get ECR repository URIs
      id: ecr-repos
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        REGION=${{ vars.AWS_REGION }}
        echo "backend=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ENV}/wumbo/backend" >> $GITHUB_OUTPUT
        echo "frontend=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ENV}/wumbo/frontend" >> $GITHUB_OUTPUT
        echo "worker=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ENV}/wumbo/worker" >> $GITHUB_OUTPUT
        echo "migrations=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ENV}/wumbo/migrations" >> $GITHUB_OUTPUT

    - name: Build and push Backend image
      if: needs.detect-changes.outputs.backend == 'true'
      uses: docker/build-push-action@v5
      with:
        context: ./backend
        file: ./backend/Dockerfile
        platforms: linux/arm64  # Graviton support
        push: true
        tags: |
          ${{ steps.ecr-repos.outputs.backend }}:latest
          ${{ steps.ecr-repos.outputs.backend }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
        build-args: |
          ENVIRONMENT=${{ needs.determine-environment.outputs.environment }}

    - name: Build and push Frontend image
      if: needs.detect-changes.outputs.web == 'true' || needs.detect-changes.outputs.ui == 'true'
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./apps/web/Dockerfile
        platforms: linux/arm64
        push: true
        tags: |
          ${{ steps.ecr-repos.outputs.frontend }}:latest
          ${{ steps.ecr-repos.outputs.frontend }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Build and push Worker image
      if: needs.detect-changes.outputs.worker == 'true' || needs.detect-changes.outputs.backend == 'true'
      uses: docker/build-push-action@v5
      with:
        context: ./worker
        file: ./worker/Dockerfile
        platforms: linux/arm64
        push: true
        tags: |
          ${{ steps.ecr-repos.outputs.worker }}:latest
          ${{ steps.ecr-repos.outputs.worker }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Build and push Migrations image
      if: needs.detect-changes.outputs.migrations == 'true'
      uses: docker/build-push-action@v5
      with:
        context: ./backend
        file: ./backend/Dockerfile.migrations
        platforms: linux/arm64
        push: true
        tags: |
          ${{ steps.ecr-repos.outputs.migrations }}:latest
          ${{ steps.ecr-repos.outputs.migrations }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

### Run Database Migrations

```yaml
run-migrations:
  name: Run Database Migrations
  needs: [build-and-push, detect-changes, determine-environment]
  if: needs.detect-changes.outputs.migrations == 'true'
  runs-on: ubuntu-latest
  environment: ${{ needs.determine-environment.outputs.environment }}

  steps:
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION }}

    - name: Run migrations via ECS Task
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}

        echo "🔄 Running database migrations..."

        # Run one-off ECS task for migrations
        TASK_ARN=$(aws ecs run-task \
          --cluster ${ENV}-wumbo-cluster \
          --task-definition ${ENV}-wumbo-migrations \
          --launch-type FARGATE \
          --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
          --query 'tasks[0].taskArn' \
          --output text)

        echo "Migration task: $TASK_ARN"

        # Wait for task to complete
        aws ecs wait tasks-stopped \
          --cluster ${ENV}-wumbo-cluster \
          --tasks $TASK_ARN

        # Check exit code
        EXIT_CODE=$(aws ecs describe-tasks \
          --cluster ${ENV}-wumbo-cluster \
          --tasks $TASK_ARN \
          --query 'tasks[0].containers[0].exitCode' \
          --output text)

        if [ "$EXIT_CODE" != "0" ]; then
          echo "❌ Migration failed with exit code: $EXIT_CODE"
          exit 1
        fi

        echo "✅ Migrations completed successfully"
```

### Deploy ECS Services

```yaml
deploy-services:
  name: Deploy ECS Services
  needs: [build-and-push, run-migrations, detect-changes, determine-environment]
  if: always() && needs.build-and-push.result == 'success'
  runs-on: ubuntu-latest
  environment: ${{ needs.determine-environment.outputs.environment }}

  steps:
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION }}

    - name: Deploy Backend service
      if: needs.detect-changes.outputs.backend == 'true'
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}
        echo "🚀 Deploying Backend service..."

        aws ecs update-service \
          --cluster ${ENV}-wumbo-cluster \
          --service ${ENV}-wumbo-backend \
          --force-new-deployment \
          --region ${{ vars.AWS_REGION }}

        echo "✅ Backend deployment initiated"

    - name: Deploy Frontend service
      if: needs.detect-changes.outputs.web == 'true' || needs.detect-changes.outputs.ui == 'true'
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}
        echo "🚀 Deploying Frontend service..."

        aws ecs update-service \
          --cluster ${ENV}-wumbo-cluster \
          --service ${ENV}-wumbo-frontend \
          --force-new-deployment \
          --region ${{ vars.AWS_REGION }}

        echo "✅ Frontend deployment initiated"

    - name: Deploy Worker service
      if: needs.detect-changes.outputs.worker == 'true' || needs.detect-changes.outputs.backend == 'true'
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}
        echo "🚀 Deploying Worker service..."

        aws ecs update-service \
          --cluster ${ENV}-wumbo-cluster \
          --service ${ENV}-wumbo-worker \
          --force-new-deployment \
          --region ${{ vars.AWS_REGION }}

        echo "✅ Worker deployment initiated"

    - name: Wait for services to stabilize
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}
        echo "⏳ Waiting for services to stabilize..."

        SERVICES=""

        if [ "${{ needs.detect-changes.outputs.backend }}" == "true" ]; then
          SERVICES="$SERVICES ${ENV}-wumbo-backend"
        fi

        if [ "${{ needs.detect-changes.outputs.web }}" == "true" ] || [ "${{ needs.detect-changes.outputs.ui }}" == "true" ]; then
          SERVICES="$SERVICES ${ENV}-wumbo-frontend"
        fi

        if [ "${{ needs.detect-changes.outputs.worker }}" == "true" ] || [ "${{ needs.detect-changes.outputs.backend }}" == "true" ]; then
          SERVICES="$SERVICES ${ENV}-wumbo-worker"
        fi

        if [ -n "$SERVICES" ]; then
          echo "Waiting for: $SERVICES"
          aws ecs wait services-stable \
            --cluster ${ENV}-wumbo-cluster \
            --services $SERVICES \
            --region ${{ vars.AWS_REGION }}
          echo "✅ All services are stable"
        fi
```

### Post-Deployment Validation

```yaml
post-deployment-validation:
  name: Post-Deployment Validation
  needs: [deploy-services, determine-environment]
  runs-on: ubuntu-latest

  steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'

    - name: Install dependencies
      run: |
        cd tests/e2e
        npm ci

    - name: Health check - Backend
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}

        # Get backend URL from AWS (ALB or domain)
        BACKEND_URL=$(aws ssm get-parameter \
          --name "/${ENV}/wumbo/backend-url" \
          --query 'Parameter.Value' \
          --output text)

        echo "Checking health at: $BACKEND_URL/health"

        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" ${BACKEND_URL}/health)

        if [ "$RESPONSE" != "200" ]; then
          echo "❌ Health check failed: HTTP $RESPONSE"
          exit 1
        fi

        echo "✅ Backend is healthy"

    - name: Health check - Frontend
      run: |
        ENV=${{ needs.determine-environment.outputs.environment }}

        FRONTEND_URL=$(aws ssm get-parameter \
          --name "/${ENV}/wumbo/frontend-url" \
          --query 'Parameter.Value' \
          --output text)

        echo "Checking health at: $FRONTEND_URL/api/health"

        RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" ${FRONTEND_URL}/api/health)

        if [ "$RESPONSE" != "200" ]; then
          echo "❌ Health check failed: HTTP $RESPONSE"
          exit 1
        fi

        echo "✅ Frontend is healthy"

    - name: Run smoke tests
      run: |
        cd tests/e2e
        npm run test:smoke
      env:
        API_URL: ${{ secrets.API_URL }}
        WEB_URL: ${{ secrets.WEB_URL }}
```

---

## Environment Configuration

### GitHub Environments

Create three GitHub environments:
1. **development** - Auto-deploy from `development` branch
2. **staging** - Auto-deploy from `staging` branch
3. **production** - Auto-deploy from `main` branch, requires manual approval

### GitHub Secrets (per environment)

```
AWS_ACCESS_KEY_ID          - AWS credentials for deployments
AWS_SECRET_ACCESS_KEY      - AWS credentials for deployments
DATABASE_URL               - Connection string for tests
PLAID_CLIENT_ID           - Plaid sandbox/dev keys
PLAID_SECRET              - Plaid sandbox/dev keys
EXPO_TOKEN                - Expo EAS token for mobile builds
CODECOV_TOKEN             - Code coverage reporting
SLACK_WEBHOOK_URL         - Deployment notifications
```

### GitHub Variables (per environment)

```
AWS_REGION                - us-east-1
ENVIRONMENT_NAME          - development/staging/production
API_URL                   - Backend API URL
WEB_URL                   - Frontend URL
```

---

## Branching Strategy

### Branch → Environment Mapping

```
main        → production  (requires approval)
staging     → staging     (auto-deploy)
development → development (auto-deploy)
feature/*   → No deployment (tests only)
```

### Git Flow

1. **Feature Development**
   ```bash
   git checkout -b feature/add-budget-alerts development
   # Make changes
   git push origin feature/add-budget-alerts
   # Open PR → development
   ```

2. **Development Testing**
   ```bash
   # After PR merge to development
   # Auto-deploys to development environment
   ```

3. **Staging Release**
   ```bash
   git checkout staging
   git merge development
   git push origin staging
   # Auto-deploys to staging environment
   ```

4. **Production Release**
   ```bash
   git checkout main
   git merge staging
   git push origin main
   # Requires manual approval
   # Then auto-deploys to production
   ```

---

## Quality Gates

### Pull Request Requirements

Before merge, PRs must pass:
- ✅ All linters pass (Ruff, ESLint)
- ✅ All formatters pass (Ruff, Prettier)
- ✅ All type checks pass (MyPy, TypeScript)
- ✅ All unit tests pass (>80% coverage)
- ✅ Build succeeds (all packages)
- ✅ Security scan passes (no high/critical vulnerabilities)
- ✅ At least one approval (for main/staging branches)

### Deployment Requirements

Before deployment:
- ✅ All quality gates pass
- ✅ Docker images build successfully
- ✅ Database migrations (if any) succeed
- ✅ Previous deployment succeeded (no rollback in progress)

---

## Mobile App CI/CD

### EAS Build

```yaml
mobile-build:
  name: Build Mobile App
  runs-on: ubuntu-latest

  steps:
    - uses: actions/checkout@v4

    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'

    - name: Set up Expo
      uses: expo/expo-github-action@v8
      with:
        expo-version: latest
        token: ${{ secrets.EXPO_TOKEN }}

    - name: Install dependencies
      run: |
        cd apps/mobile
        npm ci

    - name: Build iOS (Development)
      if: github.ref != 'refs/heads/main'
      run: |
        cd apps/mobile
        eas build --platform ios --profile development --non-interactive

    - name: Build iOS (Production)
      if: github.ref == 'refs/heads/main'
      run: |
        cd apps/mobile
        eas build --platform ios --profile production --non-interactive

    - name: Build Android (Development)
      if: github.ref != 'refs/heads/main'
      run: |
        cd apps/mobile
        eas build --platform android --profile development --non-interactive

    - name: Build Android (Production)
      if: github.ref == 'refs/heads/main'
      run: |
        cd apps/mobile
        eas build --platform android --profile production --non-interactive
```

### App Store Submission

```yaml
mobile-submit:
  name: Submit to App Stores
  runs-on: ubuntu-latest
  # Only manual trigger for submissions
  if: github.event_name == 'workflow_dispatch'

  steps:
    - uses: actions/checkout@v4

    - name: Set up Expo
      uses: expo/expo-github-action@v8
      with:
        expo-version: latest
        token: ${{ secrets.EXPO_TOKEN }}

    - name: Submit to App Store
      run: |
        cd apps/mobile
        eas submit --platform ios --latest --non-interactive

    - name: Submit to Play Store
      run: |
        cd apps/mobile
        eas submit --platform android --latest --non-interactive
```

---

## Monitoring & Observability

### Deployment Tracking

- **Grafana annotation** - Mark deployments on Grafana dashboards
- **Sentry release tracking** - Track errors by release
- **CloudWatch logs** - Deployment logs retained

### Metrics to Track

- Deployment frequency
- Lead time for changes
- Mean time to recovery (MTTR)
- Change failure rate
- Build success rate
- Test coverage trend

---

## Rollback Procedures

### Automatic Rollback

Not implemented - manual rollback required.

### Manual Rollback

```bash
# 1. Identify last known good deployment
aws ecs describe-services \
  --cluster production-wumbo-cluster \
  --services production-wumbo-backend

# 2. Get task definition ARN of previous version
PREVIOUS_TASK_DEF="arn:aws:ecs:..."

# 3. Update service to previous task definition
aws ecs update-service \
  --cluster production-wumbo-cluster \
  --service production-wumbo-backend \
  --task-definition $PREVIOUS_TASK_DEF \
  --force-new-deployment

# 4. Wait for rollback to complete
aws ecs wait services-stable \
  --cluster production-wumbo-cluster \
  --services production-wumbo-backend
```

### Database Rollback

```bash
# If migrations need to be rolled back
cd backend
alembic downgrade -1  # Rollback one migration

# Or to specific revision
alembic downgrade <revision_id>
```

---

## Security Considerations

### Secrets Management

- **GitHub Secrets** - Encrypted secrets per environment
- **AWS Secrets Manager** - Runtime secrets (DB creds, API keys)
- **Never commit secrets** - Use `.env.example` templates
- **Rotate regularly** - Automate secret rotation

### Image Scanning

- **Trivy** - Scan Docker images for vulnerabilities
- **Fail on high/critical** - Block deployment if critical CVEs found
- **SBOM generation** - Track dependencies

### Dependency Updates

- **Dependabot** - Automated dependency PRs
- **Security-only mode** - Auto-merge security patches (dev only)
- **Weekly updates** - Review and merge non-security updates

---

## Cost Optimization

### GitHub Actions

- **Concurrency limits** - Cancel outdated workflow runs
- **Path filtering** - Only build what changed
- **Cache aggressively** - npm, pip, Docker layers
- **Self-hosted runners** (optional) - For high-frequency repos

### Example Concurrency

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## Implementation Checklist

### Phase 1 (Weeks 1-2)
- [ ] Create main CI/CD workflow (`deploy.yml`)
- [ ] Set up GitHub environments (dev, staging, prod)
- [ ] Configure AWS credentials in GitHub secrets
- [ ] Implement quality checks (linting, tests)
- [ ] Implement change detection
- [ ] Set up Docker build and push
- [ ] Test deployment to development

### Phase 2 (Weeks 3-4)
- [ ] Add database migration workflow
- [ ] Implement post-deployment validation
- [ ] Add mobile app build workflow
- [ ] Configure Expo EAS
- [ ] Add security scanning
- [ ] Set up notifications

### Phase 3 (Weeks 5-6)
- [ ] Add PR preview environments (optional)
- [ ] Implement E2E tests in CI
- [ ] Add performance testing
- [ ] Set up monitoring/metrics
- [ ] Document runbooks
- [ ] Train team on workflows

---

*This CI/CD strategy ensures reliable, automated deployments while maintaining high code quality and security standards.*
