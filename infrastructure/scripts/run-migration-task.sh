#!/bin/bash
# Run database migrations via ECS Fargate task
#
# Usage:
#   ./scripts/run-migration-task.sh <environment>
#
# Example:
#   ./scripts/run-migration-task.sh development
#   ./scripts/run-migration-task.sh production

set -e

ENVIRONMENT=${1:-development}

echo "========================================"
echo "Running Database Migrations via ECS"
echo "========================================"
echo "Environment: $ENVIRONMENT"
echo ""

# Get stack outputs
echo "📋 Getting stack information..."
CLUSTER_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${ENVIRONMENT}-ComputeStack" \
  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
  --output text)

TASK_DEF_ARN=$(aws cloudformation describe-stacks \
  --stack-name "${ENVIRONMENT}-ComputeStack" \
  --query "Stacks[0].Outputs[?OutputKey=='MigrationTaskDefinitionArn'].OutputValue" \
  --output text)

VPC_ID=$(aws cloudformation describe-stacks \
  --stack-name "${ENVIRONMENT}-SecurityStack" \
  --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue" \
  --output text)

echo "✓ Cluster: $CLUSTER_NAME"
echo "✓ Task Definition: $TASK_DEF_ARN"
echo ""

# Get private subnets
echo "📋 Getting network configuration..."
SUBNETS=$(aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*Private*" \
  --query "Subnets[*].SubnetId" \
  --output text | tr '\t' ',')

# Get migration security group
SECURITY_GROUP=$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*MigrationSecurityGroup*" \
  --query "SecurityGroups[0].GroupId" \
  --output text)

echo "✓ Subnets: $SUBNETS"
echo "✓ Security Group: $SECURITY_GROUP"
echo ""

# Run migration task
echo "🚀 Starting migration task..."
TASK_ARN=$(aws ecs run-task \
  --cluster "$CLUSTER_NAME" \
  --task-definition "$TASK_DEF_ARN" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
  --query "tasks[0].taskArn" \
  --output text)

echo "✓ Task started: $TASK_ARN"
echo ""

# Wait for task to complete
echo "⏳ Waiting for migration to complete..."
echo "(This may take a few minutes...)"
echo ""

aws ecs wait tasks-stopped \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN"

# Check exit code
EXIT_CODE=$(aws ecs describe-tasks \
  --cluster "$CLUSTER_NAME" \
  --tasks "$TASK_ARN" \
  --query "tasks[0].containers[0].exitCode" \
  --output text)

echo ""
if [ "$EXIT_CODE" = "0" ]; then
  echo "✅ Migration completed successfully!"
  echo ""
  echo "📝 View logs:"
  echo "   aws logs tail /aws/ecs/${ENVIRONMENT}-wumbo-cluster/migration --follow"
  exit 0
else
  echo "❌ Migration failed with exit code: $EXIT_CODE"
  echo ""
  echo "📝 View error logs:"
  echo "   aws logs tail /aws/ecs/${ENVIRONMENT}-wumbo-cluster/migration --follow"
  exit 1
fi
