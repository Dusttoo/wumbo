# Database Migrations Guide

This guide explains how to manage database migrations for the Wumbo backend.

## Overview

We use Alembic for database migrations with automated ECS task execution for production deployments.

## Local Development

### Create a New Migration

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "add user preferences table"

# Create empty migration for manual changes
alembic revision -m "add custom index"
```

### Apply Migrations Locally

```bash
# Apply all pending migrations
python scripts/run_migrations.py

# Check for pending migrations without applying
python scripts/run_migrations.py --check-only

# Downgrade one migration (use with caution!)
python scripts/run_migrations.py --downgrade 1
```

### Manual Alembic Commands

```bash
# Show current revision
alembic current

# Show migration history
alembic history

# Upgrade to specific revision
alembic upgrade <revision>

# Downgrade to specific revision
alembic downgrade <revision>

# Show SQL that would be executed
alembic upgrade head --sql
```

## Production Deployments

### Automated Migration (Recommended)

Migrations run automatically after successful backend deployments via GitHub Actions.

**Manual trigger via GitHub UI:**
1. Go to Actions → "Run Database Migrations"
2. Click "Run workflow"
3. Select environment (development/staging/production)
4. Click "Run workflow"

### Manual Migration via ECS

Run migrations manually using the ECS task:

```bash
cd infrastructure

# Development
./scripts/run-migration-task.sh development

# Production
./scripts/run-migration-task.sh production
```

### Manual Migration via AWS CLI

```bash
# Get cluster and task definition
CLUSTER=$(aws cloudformation describe-stacks \
  --stack-name production-ComputeStack \
  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
  --output text)

TASK_DEF=$(aws cloudformation describe-stacks \
  --stack-name production-ComputeStack \
  --query "Stacks[0].Outputs[?OutputKey=='MigrationTaskDefinitionArn'].OutputValue" \
  --output text)

# Get network configuration (subnets and security group)
# ... (see infrastructure/scripts/run-migration-task.sh for full example)

# Run migration task
aws ecs run-task \
  --cluster "$CLUSTER" \
  --task-definition "$TASK_DEF" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[...],securityGroups=[...],assignPublicIp=DISABLED}"
```

## Migration Best Practices

### 1. Always Test Migrations

```bash
# Test locally first
python scripts/run_migrations.py

# Then test in development environment
./infrastructure/scripts/run-migration-task.sh development

# Finally run in production
./infrastructure/scripts/run-migration-task.sh production
```

### 2. Backwards Compatible Migrations

Make migrations backwards compatible when possible:

**Adding a column:**
```python
# Good: Nullable column or with default
op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

# Or with default
op.add_column('users', sa.Column('status', sa.String(20), server_default='active'))
```

**Removing a column (multi-step process):**
```python
# Step 1: Make column nullable (deploy this first)
op.alter_column('users', 'old_field', nullable=True)

# Step 2: Remove column (deploy after code changes)
op.drop_column('users', 'old_field')
```

### 3. Data Migrations

For complex data transformations, use a separate migration:

```python
def upgrade():
    # Schema change
    op.add_column('transactions', sa.Column('category_id', sa.UUID()))

    # Data migration
    connection = op.get_bind()
    connection.execute(
        text("""
            UPDATE transactions t
            SET category_id = c.id
            FROM categories c
            WHERE t.category_name = c.name
        """)
    )

def downgrade():
    op.drop_column('transactions', 'category_id')
```

### 4. Review Before Deploying

```bash
# Check what will be executed
alembic upgrade head --sql > migration.sql
cat migration.sql  # Review the SQL
```

## Troubleshooting

### Migration Stuck or Failed

**Check logs:**
```bash
# Via AWS CLI
aws logs tail /aws/ecs/production-wumbo-cluster/migration --follow

# Via CloudWatch Console
# Go to CloudWatch → Log Groups → /aws/ecs/production-wumbo-cluster/migration
```

**Check task status:**
```bash
# List recent migration tasks
aws ecs list-tasks --cluster production-wumbo-cluster --family production-wumbo-migration

# Get task details
aws ecs describe-tasks --cluster production-wumbo-cluster --tasks <task-arn>
```

### Alembic Out of Sync

**Stamp database to specific revision:**
```bash
# If database is ahead of migrations
alembic stamp head

# If database needs to be set to specific revision
alembic stamp <revision>
```

### Roll Back Migration

```bash
# Locally
python scripts/run_migrations.py --downgrade 1

# In ECS (requires custom task run with downgrade command)
# Not recommended - fix forward instead!
```

## Emergency Procedures

### Database is in Inconsistent State

1. **Identify the issue:**
   ```bash
   alembic current
   alembic history
   ```

2. **Create fix-forward migration:**
   ```bash
   alembic revision -m "fix inconsistent state"
   # Edit migration file to fix the issue
   ```

3. **Test locally:**
   ```bash
   python scripts/run_migrations.py
   ```

4. **Deploy fix:**
   ```bash
   ./infrastructure/scripts/run-migration-task.sh production
   ```

### Need to Skip a Migration

```bash
# Locally or via bastion host:
alembic stamp <next-revision>
```

**⚠️ Warning:** Only do this if you're absolutely sure the migration isn't needed or has already been manually applied.

## Migration Checklist

Before deploying a migration to production:

- [ ] Migration tested locally
- [ ] Migration tested in development environment
- [ ] Migration is backwards compatible (if possible)
- [ ] Data backup taken (for critical changes)
- [ ] Migration reviewed by team
- [ ] Rollback plan documented
- [ ] Deployment window scheduled (for large migrations)

## File Structure

```
backend/
├── alembic/
│   ├── versions/          # Migration files
│   ├── env.py            # Alembic environment config
│   └── script.py.mako    # Migration template
├── alembic.ini           # Alembic configuration
└── scripts/
    └── run_migrations.py # Migration runner script

infrastructure/
└── scripts/
    └── run-migration-task.sh  # ECS migration runner

.github/workflows/
└── run-migrations.yml    # CI/CD migration workflow
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [AWS ECS Task Execution](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_run_task.html)
