# Monitoring & Domain Strategy

This document summarizes the cost-optimized monitoring approach and flexible domain handling for the Wumbo app.

## Monitoring Strategy: Prometheus + Grafana

### Why Not CloudWatch?

CloudWatch can get expensive quickly with custom metrics and dashboards:
- Custom metrics: $0.30 per metric per month
- Dashboards: $3 per dashboard per month
- Logs: $0.50 per GB ingested
- Insights queries: Additional charges

For a typical app with ~50 custom metrics and 5 dashboards, this could cost **$20-30/month** or more.

### Our Approach: Self-Hosted Monitoring

We use **Prometheus + Grafana running on ECS Fargate** following the proven pattern from cipher-dnd-bot:

**Prometheus** (Metrics Collection):
- Runs as ECS Fargate service
- Scrapes metrics from all services via CloudMap service discovery
- Stores time-series data on EFS (15-day retention)
- Cost: Only ECS task runtime (~$7-10/month)

**Grafana** (Dashboards & Visualization):
- Runs as ECS Fargate service
- Pre-configured with Prometheus datasource
- Pre-provisioned dashboards for all key metrics
- Web UI accessible via ALB
- Cost: Only ECS task runtime (~$7-10/month)

**Metric Exporters**:
- PostgreSQL exporter (sidecar) - RDS metrics
- Redis exporter (sidecar) - ElastiCache metrics
- FastAPI native `/metrics` endpoint - application metrics

### Cost Comparison

| Component | CloudWatch Approach | Prometheus/Grafana Approach | Savings |
|-----------|---------------------|------------------------------|---------|
| Dashboards | $15/month (5 dashboards) | $0 (Grafana) | $15 |
| Custom Metrics | $15/month (50 metrics) | $0 (Prometheus) | $15 |
| Logs (minimal retention) | $5/month | $0.05/month (3-day retention) | $5 |
| Infrastructure | $0 (managed service) | $15/month (EFS + ECS tasks) | -$15 |
| **Total** | **$35/month** | **$15/month** | **$20/month** |

### What We Still Use CloudWatch For

We keep CloudWatch for **critical alarms only** (< 5 alarms):
- All ECS tasks down (CRITICAL)
- Database storage < 5GB (CRITICAL)
- Database CPU > 95% for 15+ min
- High sustained error rate (production only)

These basic alarms are essentially **free** as they use default metrics.

### Accessing Monitoring

**With Custom Domain** (when configured):
- Grafana: `https://grafana.yourdomain.com`
- Prometheus: `https://prometheus.yourdomain.com` (optional, mostly internal)

**Without Custom Domain** (development):
- Grafana: `https://dev-monitoring-abc123.us-east-1.elb.amazonaws.com`
- Prometheus: `https://dev-monitoring-abc123.us-east-1.elb.amazonaws.com:9090`

### Pre-Built Dashboards

1. **Application Overview**
   - Request rate, latency (p50, p95, p99)
   - Error rates (4xx, 5xx)
   - Active users and sessions

2. **ECS Services Health**
   - CPU/memory utilization per service
   - Task count and restart frequency
   - Network throughput

3. **Database Performance**
   - Connection pool usage
   - Query performance
   - Cache hit ratio
   - Transaction rate

4. **Redis Performance**
   - Memory usage and evictions
   - Commands per second
   - Key hit/miss ratio

5. **Plaid Integration**
   - Sync success/failure rates
   - API call latency
   - Webhook delivery status

6. **Business Metrics**
   - Bill reminders sent
   - Budget alerts triggered
   - New user sign-ups
   - Active households

---

## Domain Strategy: Flexible & Optional

### Design Principle

**The app works perfectly without a custom domain.** Domain configuration is completely optional and can be added later without major changes.

### Domain Configuration by Environment

#### Development
- **Domain**: None (not needed)
- **Access via**: ALB DNS names
  - Backend: `dev-backend-1234567.us-east-1.elb.amazonaws.com`
  - Frontend: `dev-frontend-7654321.us-east-1.elb.amazonaws.com`
  - Grafana: `dev-monitoring-9876543.us-east-1.elb.amazonaws.com`
- **SSL**: Self-signed or ALB-provided certificate
- **Cost**: $0

#### Staging (Optional Domain)
- **Domain**: Can use custom domain if you want
  - `api-staging.yourdomain.com`
  - `app-staging.yourdomain.com`
  - `grafana-staging.yourdomain.com`
- **Fallback**: ALB DNS names work fine
- **SSL**: ACM certificate (free)
- **Cost**: Route53 hosted zone ($0.50/month) if using domain

#### Production (Custom Domain Recommended)
- **Domain**: Custom domain for professional appearance
  - `api.yourdomain.com`
  - `app.yourdomain.com`
  - `grafana.yourdomain.com`
- **SSL**: ACM certificate (free, auto-renewing)
- **Cost**: Route53 hosted zone ($0.50/month) + domain registration (~$12/year)

### When to Add a Domain

**Don't add a domain until**:
- ✅ You've chosen a domain name
- ✅ You're ready to register it
- ✅ You're deploying to staging/production
- ✅ You want user-friendly URLs

**You can start development immediately** without a domain by:
1. Setting `domain_name: null` in cdk.context.json
2. Deploying infrastructure
3. Using ALB DNS names
4. Adding domain later when ready

### Adding a Domain Later

When you're ready to add a domain:

1. **Update cdk.context.json**:
   ```json
   {
     "production": {
       "domain_name": "yourdomain.com"
     }
   }
   ```

2. **Deploy DnsStack**:
   ```bash
   make deploy-dns ENV=production
   ```

3. **Get NS records**:
   ```bash
   aws route53 list-hosted-zones-by-name --dns-name yourdomain.com
   ```

4. **Configure with registrar**:
   - Copy the 4 NS records
   - Update at your domain registrar (GoDaddy, Namecheap, etc.)
   - Wait 5-10 minutes for DNS propagation

5. **Redeploy ComputeStack** (to use certificate):
   ```bash
   make deploy-compute ENV=production
   ```

6. **Done!** Your services are now accessible via custom domain.

### DnsStack Structure

The DnsStack is:
- **Optional** - only created if `domain_name` is configured
- **Independent** - doesn't block other stacks
- **Modular** - can be added/removed without affecting services
- **Environment-specific** - different domains per environment if desired

### Architecture Pattern

```python
# In app.py
domain_name = env_config.get("domain_name")
dns_stack = None

if domain_name:
    # Only create DNS stack if domain is configured
    dns_stack = DnsStack(
        app, f"{environment}-DnsStack",
        domain_name=domain_name,
        env_name=environment,
        ...
    )

# ComputeStack handles both scenarios
compute_stack = ComputeStack(
    app, f"{environment}-ComputeStack",
    certificate=dns_stack.certificate if dns_stack else None,
    hosted_zone=dns_stack.hosted_zone if dns_stack else None,
    ...
)
```

If `dns_stack` is None:
- ComputeStack creates ALB without custom domain
- Services accessible via ALB DNS names
- Self-signed or AWS-provided certificates

If `dns_stack` exists:
- ComputeStack uses ACM certificate
- Route53 A records created
- Services accessible via custom domain

---

## Cost Summary

### Monthly Costs (Development Environment)

| Component | With CloudWatch | With Prometheus/Grafana |
|-----------|-----------------|-------------------------|
| Monitoring | $35 | $15 |
| Domain (optional) | $0.50 | $0.50 |
| **Total Monitoring** | **$35.50** | **$15.50** |

**Savings**: ~$20/month

### Why This Matters

For personal/small-scale use:
- Development environment runs 24/7
- Monitoring costs add up quickly
- **$20/month = $240/year** saved
- EFS + ECS approach is more cost-effective
- Proven pattern from cipher-dnd-bot

### Additional Benefits

**Beyond cost savings**:
- Better dashboards (Grafana is superior to CloudWatch)
- More flexible alerting (Prometheus AlertManager if needed)
- Exportable dashboards (JSON configs)
- Industry-standard tools (transferable knowledge)
- No vendor lock-in (can move to any infrastructure)

---

## Implementation Notes

### From cipher-dnd-bot

The monitoring approach is directly based on your cipher-dnd-bot implementation:
- Same EFS setup with access points
- Same Prometheus configuration via SSM
- Same Grafana provisioning pattern
- Same service discovery approach
- Same ALB pattern for external access

### Key Files to Reference

When implementing, reference these from cipher-dnd-bot:
- `infrastructure/stacks/monitoring_stack.py` - Complete implementation
- Prometheus scrape config generation
- Grafana datasource provisioning
- EFS access point setup
- Security group configuration

### What's Different for Wumbo

Compared to cipher-dnd-bot monitoring:
- Additional exporters: postgres_exporter, redis_exporter
- Business metrics dashboards (bills, budgets, Plaid)
- Optional domain handling (cipher-dnd-bot always has domain)
- Simpler alarm strategy (fewer critical alarms)

---

*This strategy ensures you can start development immediately without a domain, while keeping monitoring costs low with the proven Prometheus/Grafana pattern from cipher-dnd-bot.*
