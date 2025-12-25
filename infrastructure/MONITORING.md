# Wumbo Monitoring Stack

Complete monitoring and observability solution using Prometheus for metrics collection and Grafana for visualization.

## Overview

The monitoring stack provides:
- **Prometheus**: Time-series metrics collection and storage
- **Grafana**: Dashboarding and visualization
- **CloudWatch Alarms**: Automated alerting for critical metrics
- **SNS**: Alert notifications via email
- **EFS**: Persistent storage for metrics and dashboards

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet/Users                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼─────┐
                    │ Grafana  │
                    │   ALB    │
                    └────┬─────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐      ┌───▼────┐     ┌────▼────┐
   │Prometheus│◄─────┤Grafana │     │CloudWatch│
   │         │      │        │     │ Alarms  │
   └────┬────┘      └───┬────┘     └────┬────┘
        │               │               │
        │          ┌────▼────┐          │
        │          │   EFS   │          │
        │          │ Storage │          │
        │          └─────────┘          │
        │                               │
   ┌────▼───────────────────────────────▼────┐
   │     Application Services (Backend,      │
   │     Worker, Beat, Database, Redis)      │
   └─────────────────────────────────────────┘
```

## Components

### Prometheus
- **Purpose**: Metrics collection and storage
- **Metrics Retention**: 15 days
- **Scrape Interval**: Configurable (default: 15s)
- **Storage**: EFS for persistence
- **Access**: Internal only via service discovery

### Grafana
- **Purpose**: Metrics visualization and dashboarding
- **Access**: Public via ALB (HTTP on port 80)
- **Default Credentials**: admin / changeme (CHANGE IN PRODUCTION!)
- **Data Sources**: Prometheus (pre-configured)
- **Storage**: EFS for dashboards and settings

### CloudWatch Alarms
- **Backend CPU > 80%**: Alerts on high CPU usage
- **Backend Memory > 80%**: Alerts on high memory usage
- **Database CPU > 80%**: Alerts on high database CPU
- **Database Connections > 80**: Alerts on connection exhaustion

### SNS Notifications
- **Topic**: Alarm notifications
- **Subscribers**: Email (configurable in cdk.json)
- **Destinations**: Can be extended to Slack, PagerDuty, etc.

## Accessing Grafana

### Get Grafana URL

After deployment, get the Grafana URL from CloudFormation outputs:

```bash
# Get Grafana URL
aws cloudformation describe-stacks \
  --stack-name production-MonitoringStack \
  --query "Stacks[0].Outputs[?OutputKey=='GrafanaUrl'].OutputValue" \
  --output text
```

### Default Login

- **URL**: `http://<alb-dns-name>`
- **Username**: `admin`
- **Password**: `changeme`

**⚠️ IMPORTANT**: Change the default password immediately after first login!

### Change Admin Password

1. Log in to Grafana
2. Go to Configuration → Users → Admin
3. Click "Change Password"
4. Enter new password

Or via environment variable in the stack (recommended for production):
```python
# In monitoring_stack.py, update Grafana container environment:
"GF_SECURITY_ADMIN_PASSWORD": secrets_manager.secret.secret_value_from_json("grafana_password")
```

## Prometheus Configuration

### Default Scrape Targets

Prometheus is configured to scrape metrics from:
- **Backend API**: http://backend.{env}.wumbo.local:8000/metrics
- **Worker**: http://worker.{env}.wumbo.local:8000/metrics
- **Beat**: http://beat.{env}.wumbo.local:8000/metrics

### Custom prometheus.yml

To customize Prometheus configuration:

1. Create custom config file:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend.production.wumbo.local:8000']
    metrics_path: '/metrics'

  - job_name: 'worker'
    static_configs:
      - targets: ['worker.production.wumbo.local:8000']

  - job_name: 'beat'
    static_configs:
      - targets: ['beat.production.wumbo.local:8000']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

2. Mount as config file in ECS task definition (update monitoring_stack.py)

## Adding Application Metrics

### FastAPI Metrics Endpoint

Add Prometheus metrics to your FastAPI application:

```python
# backend/app/main.py
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Add metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Add middleware to track metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

### Custom Business Metrics

```python
from prometheus_client import Counter, Gauge

# Transaction metrics
transactions_total = Counter(
    'wumbo_transactions_total',
    'Total transactions processed',
    ['category', 'status']
)

active_users = Gauge(
    'wumbo_active_users',
    'Number of active users'
)

# Usage
transactions_total.labels(category='groceries', status='success').inc()
active_users.set(1234)
```

## Creating Grafana Dashboards

### Import Pre-built Dashboards

1. Log in to Grafana
2. Go to Dashboards → Import
3. Enter dashboard ID or upload JSON:
   - **FastAPI Dashboard**: 12900
   - **PostgreSQL**: 9628
   - **Redis**: 11835

### Create Custom Dashboard

1. Go to Dashboards → New Dashboard
2. Add Panel
3. Select Prometheus as data source
4. Enter PromQL query:

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time (95th percentile)
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m])
)

# Active database connections
pg_stat_activity_count

# Memory usage
container_memory_usage_bytes
```

## CloudWatch Alarms

### Configure Alarm Email

Update `cdk.json`:
```json
{
  "production": {
    "alarm_email": "ops@wumbo.app"
  }
}
```

### Add Custom Alarms

Edit `monitoring_stack.py`:

```python
# Custom alarm example
custom_alarm = cloudwatch.Alarm(
    self,
    "CustomAlarm",
    metric=cloudwatch.Metric(
        namespace="AWS/ApplicationELB",
        metric_name="TargetResponseTime",
        dimensions_map={"LoadBalancer": alb.load_balancer_full_name},
        statistic="Average",
    ),
    threshold=1.0,  # 1 second
    evaluation_periods=2,
    alarm_description="API response time is too high",
)
custom_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))
```

## Troubleshooting

### Prometheus Not Scraping Targets

1. **Check service discovery**:
```bash
# Verify services are registered
aws servicediscovery list-services

# Check instance health
aws servicediscovery list-instances \
  --service-id <service-id>
```

2. **Check Prometheus targets**:
   - Go to Prometheus UI: `http://prometheus.{env}.wumbo.local:9090`
   - Navigate to Status → Targets
   - Check for scrape errors

3. **Verify network connectivity**:
   - Ensure security groups allow Prometheus to reach targets
   - Check VPC peering if using cross-VPC monitoring

### Grafana Can't Connect to Prometheus

1. **Check data source configuration**:
   - Go to Configuration → Data Sources → Prometheus
   - URL should be: `http://prometheus.{env}.wumbo.local:9090`
   - Click "Test" to verify connectivity

2. **Check service discovery**:
```bash
# DNS resolution
nslookup prometheus.production.wumbo.local

# Test from Grafana container
docker exec -it <grafana-container> curl http://prometheus.production.wumbo.local:9090
```

### EFS Mount Issues

1. **Check EFS access points**:
```bash
# List mount targets
aws efs describe-mount-targets \
  --file-system-id <efs-id>
```

2. **Check security groups**:
   - EFS security group must allow port 2049 from monitoring security group
   - Verify inbound rules

3. **Check logs**:
```bash
# View ECS task logs
aws logs tail /aws/ecs/production-wumbo-cluster/prometheus --follow
aws logs tail /aws/ecs/production-wumbo-cluster/grafana --follow
```

## Production Best Practices

### 1. Secure Grafana Access

**Add authentication:**
- Use OAuth (Google, GitHub, etc.)
- Configure LDAP/Active Directory
- Enable HTTPS with ACM certificate

**Example OAuth configuration**:
```python
# Update Grafana environment in monitoring_stack.py
environment={
    "GF_AUTH_GOOGLE_ENABLED": "true",
    "GF_AUTH_GOOGLE_CLIENT_ID": secrets.google_client_id,
    "GF_AUTH_GOOGLE_CLIENT_SECRET": secrets.google_client_secret,
    "GF_AUTH_GOOGLE_ALLOWED_DOMAINS": "wumbo.app",
}
```

### 2. Set Up Retention Policies

**Prometheus**:
- Default: 15 days
- Adjust based on storage needs
- Configure in task command: `--storage.tsdb.retention.time=30d`

**Grafana**:
- Enable snapshot cleanup
- Archive old dashboards

### 3. Enable High Availability

**For production**, consider:
- Running 2+ Prometheus instances
- Using Thanos for long-term storage
- Deploying Grafana in HA mode with external database

### 4. Monitor the Monitors

Create alarms for monitoring services:
```python
# Prometheus health alarm
prometheus_health_alarm = cloudwatch.Alarm(
    self,
    "PrometheusUnhealthyAlarm",
    metric=prometheus_service.metric("HealthyTaskCount"),
    threshold=1,
    comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
    evaluation_periods=2,
)
```

## Cost Optimization

### Development Environment
- Use smaller ECS task sizes (256 CPU, 512 MiB)
- Reduce Prometheus retention (7 days)
- Use single AZ for EFS

### Production Environment
- Right-size based on metrics volume
- Use EFS Infrequent Access for older data
- Set up lifecycle policies for log retention

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Gallery](https://grafana.com/grafana/dashboards/)
- [AWS EFS Performance](https://docs.aws.amazon.com/efs/latest/ug/performance.html)
