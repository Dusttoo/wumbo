# GitHub Actions Workflows

This directory contains the CI/CD workflows for the Family Budget application.

## Workflows

### 1. `deploy.yml` - Main CI/CD Pipeline

**Triggers:**
- Push to `main` → Deploy to production (with approval)
- Push to `staging` → Deploy to staging
- Push to `development` → Deploy to development
- Pull requests → Run tests only (no deployment)
- Manual dispatch → Deploy to chosen environment

**What it does:**
1. Runs quality checks (linting, type checking, formatting)
2. Runs unit tests with coverage
3. Detects which parts of the codebase changed
4. Builds and pushes Docker images to ECR (only for changed services)
5. Runs database migrations (if schema changed)
6. Deploys updated services to ECS
7. Runs post-deployment health checks
8. Sends notifications

**Key features:**
- ✅ Path-based filtering (only build what changed)
- ✅ Parallel execution (faster builds)
- ✅ Docker build caching (GitHub Actions cache)
- ✅ Multi-environment support
- ✅ Automatic rollback on health check failure

### 2. `pr.yml` - Pull Request Checks

**Triggers:**
- Pull request opened, updated, or reopened

**What it does:**
1. Runs all code quality checks
2. Runs all tests
3. Verifies builds succeed
4. Runs security scanning
5. Posts summary comment on PR

**Quality gates:**
- Code formatting (Ruff, Prettier)
- Linting (Ruff, ESLint)
- Type checking (MyPy, TypeScript)
- Unit tests (>80% coverage required)
- Security scanning (Trivy, npm audit)
- Build verification (Docker images)

### 3. `mobile.yml` - Mobile App Builds

**Triggers:**
- Push to `main` → Build production app
- Push to `development` → Build development app
- Changes to `apps/mobile/**` or `packages/ui/**`
- Manual dispatch → Build specific platform/profile

**What it does:**
1. Builds iOS app via EAS Build
2. Builds Android app via EAS Build
3. Submits to app stores (manual trigger only)

**Build profiles:**
- `development` - Development builds with dev API
- `preview` - Preview builds for testing
- `production` - Production builds for app stores

## Setup Instructions

### 1. GitHub Environments

Create three environments in GitHub repository settings:

**development**
- No deployment protection
- Auto-deploy on push to `development` branch

**staging**
- Optional deployment protection
- Auto-deploy on push to `staging` branch

**production**
- Required reviewers (1+)
- Auto-deploy on push to `main` branch (after approval)

### 2. GitHub Secrets

Add these secrets for each environment:

```
AWS_ACCESS_KEY_ID          - AWS credentials
AWS_SECRET_ACCESS_KEY      - AWS secret key
EXPO_TOKEN                 - Expo token for mobile builds
CODECOV_TOKEN             - Codecov API token (optional)
```

For production mobile submission:
```
EXPO_APPLE_APP_SPECIFIC_PASSWORD       - Apple App Store password
EXPO_ANDROID_SERVICE_ACCOUNT_KEY_PATH  - Google Play service account
```

### 3. GitHub Variables

Add these variables for each environment:

```
AWS_REGION                - us-east-1
```

### 4. AWS IAM User

Create IAM user for GitHub Actions with these permissions:
- `AmazonEC2ContainerRegistryPowerUser` - ECR access
- `AmazonECS_FullAccess` - ECS deployments
- Custom policy for SSM Parameter Store read
- Custom policy for ECS task execution

Example custom policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/*-family-budget/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask",
        "ecs:DescribeTasks",
        "ecs:WaitTasksStopped"
      ],
      "Resource": "*"
    }
  ]
}
```

## Branching Strategy

```
main        → production  (requires approval)
  ↑
staging     → staging     (auto-deploy)
  ↑
development → development (auto-deploy)
  ↑
feature/*   → PR checks only
```

## Usage Examples

### Deploy to Development

```bash
git checkout development
git pull
git merge feature/my-feature
git push origin development
# Automatically deploys to development environment
```

### Deploy to Production

```bash
# 1. Merge to staging first
git checkout staging
git merge development
git push origin staging
# Wait for staging deployment and test

# 2. Merge to production
git checkout main
git merge staging
git push origin main
# Requires manual approval in GitHub
# Then automatically deploys
```

### Manual Deployment

Go to Actions tab → CI/CD Pipeline → Run workflow
- Choose environment (development/staging/production)
- Click "Run workflow"

### Build Mobile App

Go to Actions tab → Mobile App Build → Run workflow
- Choose platform (all/ios/android)
- Choose profile (development/preview/production)
- Click "Run workflow"

### Submit to App Stores

Go to Actions tab → Mobile App Build → Run workflow
- Choose platform (ios/android)
- Choose profile: production
- Click "Run workflow"
- Requires approval for production environment

## Troubleshooting

### Workflow fails at "Login to Amazon ECR"

**Problem**: AWS credentials are invalid or don't have ECR permissions

**Solution**:
1. Verify AWS credentials in GitHub secrets
2. Check IAM user has `AmazonEC2ContainerRegistryPowerUser` policy
3. Ensure credentials haven't expired

### Workflow fails at "Run migrations via ECS Task"

**Problem**: VPC configuration not found in Parameter Store

**Solution**:
1. Ensure infrastructure is deployed first
2. Check that Parameter Store has these keys:
   - `/{env}/family-budget/private-subnets`
   - `/{env}/family-budget/db-security-group`

### Workflow fails at "Wait for services to stabilize"

**Problem**: ECS service failing to start new tasks

**Solution**:
1. Check ECS service logs in CloudWatch
2. Verify Docker image was pushed successfully
3. Check ECS task definition is valid
4. Verify service has capacity (CPU/memory)

### Mobile build fails

**Problem**: Expo token invalid or build configuration error

**Solution**:
1. Verify `EXPO_TOKEN` secret is set
2. Check `eas.json` configuration in `apps/mobile`
3. Review build logs in Expo dashboard

## Monitoring

### Build Status

View workflow runs:
- Go to Actions tab in GitHub
- Filter by workflow name
- Click on specific run for details

### Deployment History

View deployments:
- Go to Deployments section in GitHub
- See all deployments by environment
- View deployment status and logs

### Metrics

Track these metrics for DORA:
- **Deployment Frequency**: How often deploying to production
- **Lead Time for Changes**: Time from commit to production
- **Mean Time to Recovery**: Time to recover from failures
- **Change Failure Rate**: Percentage of deployments causing failures

## Best Practices

1. **Always create PRs for features**
   - Never push directly to main/staging
   - Let PR checks run first
   - Get at least one code review

2. **Test in development first**
   - Deploy to development
   - Verify functionality
   - Then promote to staging

3. **Monitor deployments**
   - Check Grafana dashboards after deployment
   - Watch for error rate spikes
   - Verify health checks pass

4. **Keep main branch stable**
   - Only merge tested code from staging
   - Use feature flags for incomplete features
   - Roll back quickly if issues detected

5. **Use semantic commit messages**
   - `feat:` for new features
   - `fix:` for bug fixes
   - `chore:` for maintenance
   - `docs:` for documentation

## Related Documentation

- [CI/CD Strategy](../docs/CICD_STRATEGY.md) - Comprehensive CI/CD documentation
- [Infrastructure](../docs/INFRASTRUCTURE.md) - AWS infrastructure details
- [Monitoring](../docs/MONITORING_AND_DOMAIN_STRATEGY.md) - Observability setup

---

For questions or issues with CI/CD, refer to the main [CI/CD Strategy documentation](../docs/CICD_STRATEGY.md).
