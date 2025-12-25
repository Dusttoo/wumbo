# Wumbo Infrastructure

This directory contains the AWS CDK infrastructure code for deploying the Wumbo application to AWS.

## Architecture

The infrastructure is organized into the following stacks:

1. **SecurityStack** - VPC, Secrets Manager, KMS encryption
2. **EcrStack** - Container registries for Docker images
3. **DatabaseStack** - RDS PostgreSQL 16 with Graviton instances
4. **CacheStack** - ElastiCache Redis 7.1 for caching and Celery broker
5. **DnsStack** - Route53 hosted zones and ACM SSL certificates (optional)
6. **ComputeStack** - ECS Fargate services (Backend API, Celery Worker, Celery Beat, Migration Task)
7. **MonitoringStack** - Prometheus, Grafana, CloudWatch Alarms, and SNS notifications

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **AWS CDK** installed globally
   ```bash
   npm install -g aws-cdk
   ```

3. **Python 3.11+** installed

4. **AWS Account** bootstrapped for CDK
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/REGION
   ```

## Setup

1. **Install Python dependencies**
   ```bash
   cd infrastructure
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create Secrets in AWS Secrets Manager**

   Before deploying, you must create the required secrets in AWS Secrets Manager:

   ### Plaid Credentials
   ```bash
   aws secretsmanager create-secret \
     --name development/wumbo/plaid \
     --secret-string '{
       "client_id": "YOUR_PLAID_CLIENT_ID",
       "secret": "YOUR_PLAID_SECRET",
       "environment": "sandbox"
     }'
   ```

   ### AWS Credentials (for SES)
   ```bash
   aws secretsmanager create-secret \
     --name development/wumbo/aws \
     --secret-string '{
       "access_key_id": "YOUR_AWS_ACCESS_KEY",
       "secret_access_key": "YOUR_AWS_SECRET_KEY",
       "region": "us-east-1"
     }'
   ```

   ### App Security
   ```bash
   aws secretsmanager create-secret \
     --name development/wumbo/app-security \
     --secret-string '{
       "jwt_secret_key": "GENERATE_A_RANDOM_64_CHAR_STRING",
       "algorithm": "HS256",
       "encryption_key": "GENERATE_A_RANDOM_32_CHAR_STRING"
     }'
   ```

   **Tip:** Generate secure random strings:
   ```bash
   # JWT secret key (64 characters)
   python -c "import secrets; print(secrets.token_urlsafe(48))"

   # Encryption key (32 characters for Fernet)
   python -c "import secrets; print(secrets.token_urlsafe(24))"
   ```

## Deployment

### Development Environment

1. **Update configuration** (optional for DNS/custom domain)

   Edit `cdk.json` to configure your domain:
   ```json
   {
     "context": {
       "development": {
         "alarm_email": null,
         "domain_name": "dev.yourdomain.com",
         "api_subdomain": "api"
       }
     }
   }
   ```

2. **Synthesize CloudFormation templates**
   ```bash
   cdk synth -c environment=development
   ```

3. **Deploy all stacks**
   ```bash
   cdk deploy -c environment=development --all
   ```

4. **Deploy specific stack**
   ```bash
   cdk deploy -c environment=development development-SecurityStack
   ```

   **Note**: If using DnsStack, deploy it before ComputeStack to ensure certificates are available.

### Staging/Production Environment

Replace `development` with `staging` or `production` in the commands above.

**Important:** Update `cdk.json` with environment-specific configuration:
```json
{
  "context": {
    "development": {
      "alarm_email": null
    },
    "staging": {
      "alarm_email": "your-email@example.com"
    },
    "production": {
      "alarm_email": "your-email@example.com"
    }
  }
}
```

## Stack Outputs

After deployment, you can view the stack outputs:

```bash
aws cloudformation describe-stacks --stack-name development-ComputeStack \
  --query 'Stacks[0].Outputs'
```

Key outputs:
- `AlbDnsName` - Load balancer DNS name for backend API
- `DatabaseEndpoint` - RDS database endpoint
- `RedisEndpoint` - ElastiCache Redis endpoint

## Updating Services

### Update ECS Service with New Image

1. **Build and push Docker image** (from GitHub Actions or locally)
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

   # Build and tag
   cd ../backend
   docker build -t development-wumbo-backend:latest .
   docker tag development-wumbo-backend:latest \
     ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/development-wumbo-backend:latest

   # Push
   docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/development-wumbo-backend:latest
   ```

2. **Update ECS service**
   ```bash
   aws ecs update-service \
     --cluster development-wumbo-cluster \
     --service development-wumbo-backend \
     --force-new-deployment
   ```

## Database Migrations

### Automated Migrations via GitHub Actions

The recommended approach is to use GitHub Actions for automated migrations after backend deployments.

**Manually trigger via GitHub UI:**
1. Go to Actions → "Run Database Migrations"
2. Click "Run workflow"
3. Select environment (development/staging/production)
4. Click "Run workflow"

### Manual Migrations via ECS Task

Run migrations manually using the ECS task:

```bash
cd infrastructure

# Development
./scripts/run-migration-task.sh development

# Production
./scripts/run-migration-task.sh production
```

**Note**: The migration task automatically waits for the database to be ready before running migrations.

For more details, see [backend/MIGRATIONS.md](../backend/MIGRATIONS.md)

## Monitoring

### Grafana Dashboard

Access the Grafana dashboard for comprehensive metrics visualization:

```bash
# Get Grafana URL
aws cloudformation describe-stacks \
  --stack-name production-MonitoringStack \
  --query "Stacks[0].Outputs[?OutputKey=='GrafanaUrl'].OutputValue" \
  --output text
```

**Default Login:**
- Username: `admin`
- Password: `changeme` (CHANGE IMMEDIATELY!)

### CloudWatch Logs

- **Backend Logs**: `/aws/ecs/{env}-wumbo-cluster/backend`
- **Worker Logs**: `/aws/ecs/{env}-wumbo-cluster/worker`
- **Beat Logs**: `/aws/ecs/{env}-wumbo-cluster/beat`
- **Migration Logs**: `/aws/ecs/{env}-wumbo-cluster/migration`
- **Prometheus Logs**: `/aws/ecs/{env}-wumbo-cluster/prometheus`
- **Grafana Logs**: `/aws/ecs/{env}-wumbo-cluster/grafana`

### Other Monitoring

- **ECS Service Health**: Check ECS Console for service status
- **Database Metrics**: RDS Console shows database performance
- **Redis Metrics**: ElastiCache Console shows cache performance

For detailed monitoring documentation, see [MONITORING.md](./MONITORING.md)

## Teardown

**Warning:** This will delete all resources including databases!

```bash
# Development
cdk destroy -c environment=development --all

# Production (with confirmation)
cdk destroy -c environment=production --all
```

## Cost Optimization

The infrastructure includes several cost optimizations:

- **Development**: Single NAT Gateway, t4g.micro instances, minimal monitoring
- **Staging**: Single NAT Gateway, t4g.small instances, basic monitoring
- **Production**: Dual NAT Gateways (HA), multi-AZ RDS, enhanced monitoring

### Estimated Monthly Costs

**Development:**
- NAT Gateway: ~$32/month
- RDS t4g.micro: ~$12/month
- ElastiCache t4g.micro: ~$12/month
- ECS Fargate (5 services): ~$40-50/month
- EFS (monitoring): ~$5/month
- **Total: ~$100-110/month**

**Production:**
- NAT Gateways (2): ~$64/month
- RDS t4g.small (Multi-AZ): ~$50/month
- ElastiCache r7g.large: ~$106/month
- ECS Fargate (8-12 tasks): ~$120-180/month
- EFS (monitoring): ~$10/month
- ALB (Grafana): ~$16/month
- **Total: ~$370-430/month**

## Troubleshooting

### Stack Failed to Deploy

1. Check CloudFormation events in AWS Console
2. Look for resource limit errors (VPC limits, IP address exhaustion, etc.)
3. Verify secrets exist in Secrets Manager

### ECS Tasks Failing to Start

1. Check CloudWatch Logs for the service
2. Verify secrets are accessible from task role
3. Check security group rules allow database/Redis access
4. Ensure container image exists in ECR

### Database Connection Issues

1. Verify security group ingress rules
2. Check database is in AVAILABLE state
3. Verify correct database credentials in secret

## Next Steps

### Completed ✅
- ✅ **SSL/TLS certificates** - ACM certificates with DNS validation
- ✅ **Custom domain support** - Route53 hosted zones and A records
- ✅ **Prometheus/Grafana monitoring** - Full observability stack
- ✅ **Automated database migrations** - ECS task with GitHub Actions
- ✅ **Security enhancements** - Fernet encryption for tokens, webhook verification

### Remaining Tasks
1. **Set up CI/CD pipelines** - GitHub Actions workflows for automated backend deployments
2. **Add WAF** - Web Application Firewall for production security
3. **Set up automated backups** - RDS automated snapshots and backup retention policies
4. **Implement secrets rotation** - Automatic rotation for database and API credentials
5. **Add disaster recovery** - Cross-region backups and recovery procedures
6. **Performance testing** - Load testing and optimization

## Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [RDS PostgreSQL Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
