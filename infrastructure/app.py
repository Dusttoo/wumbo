#!/usr/bin/env python3
"""CDK app for Wumbo infrastructure"""

import os

import aws_cdk as cdk
from stacks.cache_stack import CacheStack
from stacks.compute_stack import ComputeStack
from stacks.database_stack import DatabaseStack
from stacks.dns_stack import DnsStack
from stacks.ecr_stack import EcrStack
from stacks.monitoring_stack import MonitoringStack
from stacks.security_stack import SecurityStack

# Initialize app
app = cdk.App()

# ==================== Configuration ====================

# Get configuration from context or environment
environment = app.node.try_get_context("environment") or os.environ.get(
    "ENVIRONMENT", "development"
)
account = app.node.try_get_context("account") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION", "us-east-1")

# Load environment-specific config from cdk.context.json
env_config = app.node.try_get_context(environment) or {}
alarm_email = env_config.get("alarm_email") or os.environ.get("ALARM_EMAIL")
domain_name = env_config.get("domain_name") or os.environ.get("DOMAIN_NAME", "wumbo.app")
enable_dns = env_config.get("enable_dns", False)

# Validate required configuration
if not account:
    raise ValueError("AWS account ID is required. Set CDK_DEFAULT_ACCOUNT or use 'cdk bootstrap'")

if not alarm_email and environment in ["staging", "production"]:
    print(
        f"⚠️  Warning: No alarm email configured for {environment}. Alarms will be created without email notifications."
    )

# Create AWS environment
env = cdk.Environment(account=account, region=region)

# ==================== Tags ====================

# Add tags to all resources for cost tracking and management
cdk.Tags.of(app).add("Project", "FamilyBudget")
cdk.Tags.of(app).add("Environment", environment)
cdk.Tags.of(app).add("ManagedBy", "CDK")

# Add cost allocation tags
if environment == "production":
    cdk.Tags.of(app).add("CostCenter", "production-ops")
    cdk.Tags.of(app).add("Criticality", "high")
elif environment == "staging":
    cdk.Tags.of(app).add("CostCenter", "staging-ops")
    cdk.Tags.of(app).add("Criticality", "medium")
else:
    cdk.Tags.of(app).add("CostCenter", "development")
    cdk.Tags.of(app).add("Criticality", "low")

# ==================== Stack Deployment Order ====================

print(f"🚀 Deploying Wumbo infrastructure for {environment} environment")
print(f"📍 Region: {region}")
print(f"🔑 Account: {account}")
print("")

# 1. Security Stack (VPC, Secrets, KMS)
# Must be first - provides VPC and secrets for all other stacks
security_stack = SecurityStack(
    app,
    f"{environment}-SecurityStack",
    env_name=environment,
    env=env,
    description=f"Security resources (VPC, Secrets, KMS) for {environment} Wumbo",
)

# 2. ECR Stack (Container Registries)
# Can be deployed independently
ecr_stack = EcrStack(
    app,
    f"{environment}-EcrStack",
    env_name=environment,
    env=env,
    description=f"ECR repositories for {environment} Wumbo",
)

# 3. Database Stack (RDS PostgreSQL)
# Depends on: Security Stack (VPC)
database_stack = DatabaseStack(
    app,
    f"{environment}-DatabaseStack",
    vpc=security_stack.vpc,
    env_name=environment,
    env=env,
    description=f"Database resources (RDS PostgreSQL) for {environment} Wumbo",
)
database_stack.add_dependency(security_stack)

# 4. Cache Stack (ElastiCache Redis)
# Depends on: Security Stack (VPC)
cache_stack = CacheStack(
    app,
    f"{environment}-CacheStack",
    vpc=security_stack.vpc,
    env_name=environment,
    env=env,
    description=f"Cache resources (ElastiCache Redis) for {environment} Wumbo",
)
cache_stack.add_dependency(security_stack)

# 5. DNS Stack (Route53, ACM Certificate) - Optional
# Can be deployed independently
# NOTE: Only create DNS stack if enable_dns is set to True in cdk.context.json
dns_stack = None
if enable_dns and domain_name:
    dns_stack = DnsStack(
        app,
        f"{environment}-DnsStack",
        env_name=environment,
        domain_name=domain_name,
        env=env,
        description=f"DNS and SSL certificate for {environment} Family Budget",
    )

# 6. Compute Stack (ECS Services)
# Depends on: Security Stack, Database Stack, Cache Stack, ECR Stack, DNS Stack (optional)
compute_stack = ComputeStack(
    app,
    f"{environment}-ComputeStack",
    vpc=security_stack.vpc,
    database_secret=database_stack.database_secret,
    plaid_secret=security_stack.plaid_secret,
    aws_secret=security_stack.aws_secret,
    app_secret=security_stack.app_secret,
    database_security_group=database_stack.security_group,
    cache_security_group=cache_stack.security_group,
    redis_endpoint=cache_stack.redis_endpoint,
    redis_port=cache_stack.redis_port,
    env_name=environment,
    certificate=dns_stack.certificate if dns_stack else None,
    hosted_zone=dns_stack.hosted_zone if dns_stack else None,
    api_subdomain=dns_stack.get_subdomain("api") if dns_stack else None,
    env=env,
    description=f"Compute resources (ECS) for {environment} Family Budget",
)
compute_stack.add_dependency(security_stack)
compute_stack.add_dependency(database_stack)
compute_stack.add_dependency(cache_stack)
compute_stack.add_dependency(ecr_stack)
if dns_stack:
    compute_stack.add_dependency(dns_stack)

# 6. Monitoring Stack (Prometheus, Grafana)
# Depends on: Compute Stack, Database Stack, Cache Stack
monitoring_stack = MonitoringStack(
    app,
    f"{environment}-MonitoringStack",
    vpc=security_stack.vpc,
    cluster=compute_stack.cluster,
    backend_service=compute_stack.backend_service,
    worker_service=compute_stack.worker_service,
    beat_service=compute_stack.beat_service,
    database=database_stack.database,
    cache_cluster=cache_stack.cache_cluster,
    env_name=environment,
    alarm_email=alarm_email,
    namespace=compute_stack.namespace,
    env=env,
    description=f"Monitoring resources (Prometheus, Grafana) for {environment} Family Budget",
)
monitoring_stack.add_dependency(compute_stack)
monitoring_stack.add_dependency(database_stack)
monitoring_stack.add_dependency(cache_stack)

# ==================== Stack Outputs Summary ====================

# Print deployment summary
cdk.CfnOutput(
    security_stack,
    "DeploymentSummary",
    value=f"Family Budget {environment} infrastructure deployed successfully",
    description="Deployment status",
)

# ==================== Synthesize ====================

app.synth()

print("")
print("✅ CDK synthesis complete!")
print("")
print("📦 Stacks created:")
print(f"  1. {environment}-SecurityStack (VPC, Secrets, KMS)")
print(f"  2. {environment}-EcrStack (Container Registries)")
print(f"  3. {environment}-DatabaseStack (RDS PostgreSQL)")
print(f"  4. {environment}-CacheStack (ElastiCache Redis)")
if dns_stack:
    print(f"  5. {environment}-DnsStack (Route53, SSL Certificate)")
    print(f"  6. {environment}-ComputeStack (ECS Services with HTTPS)")
    print(f"  7. {environment}-MonitoringStack (Monitoring & Alarms)")
else:
    print(f"  5. {environment}-ComputeStack (ECS Services)")
    print(f"  6. {environment}-MonitoringStack (Monitoring & Alarms)")
print("")
if dns_stack:
    print("🌐 DNS Configuration:")
    print(f"  API: https://{dns_stack.get_subdomain('api')}")
    print(f"  Web: https://{dns_stack.get_subdomain('app')}")
    print("")
    print("⚠️  IMPORTANT: First deployment with DNS/SSL:")
    print("  1. Certificate validation can take 5-10 minutes")
    if environment != "production":
        print("  2. Create NS records for subdomain delegation")
        print(f"     aws route53 list-hosted-zones --query 'HostedZones[?Name==`{environment}.{domain_name}.`]'")
    print("")
print("🚀 Next steps:")
print(f"  1. Bootstrap (if first time): cdk bootstrap -c environment={environment}")
print(f"  2. Deploy all: cdk deploy -c environment={environment} --all")
print(f"  3. Or deploy specific stack: cdk deploy -c environment={environment} SecurityStack")
print("")
