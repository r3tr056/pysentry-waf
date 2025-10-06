# PySentry WAF - Operations Manual

**Version**: 1.0.0  
**Last Updated**: October 2024

## Table of Contents

1. [System Overview](#system-overview)
2. [Deployment](#deployment)
3. [Configuration Management](#configuration-management)
4. [Monitoring & Alerting](#monitoring--alerting)
5. [Backup & Recovery](#backup--recovery)
6. [Troubleshooting](#troubleshooting)
7. [Performance Tuning](#performance-tuning)
8. [Security Operations](#security-operations)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Runbooks](#runbooks)

---

## System Overview

### Architecture Components

- **Core WAF Engine**: Request analysis and threat detection
- **Database Layer**: MongoDB for threat intelligence, Redis for caching
- **Monitoring Stack**: Prometheus metrics, structured logging
- **Performance Layer**: Async processing, caching, connection pooling

### Resource Requirements

**Minimum Production**:
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- Network: 1 Gbps

**Recommended Production**:
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 100+ GB SSD (RAID 10)
- Network: 10 Gbps

---

## Deployment

### Pre-Deployment Checklist

- [ ] MongoDB cluster configured and accessible
- [ ] Redis instance configured (6.x+)
- [ ] SSL/TLS certificates obtained
- [ ] Environment variables configured
- [ ] Firewall rules configured
- [ ] Monitoring infrastructure ready
- [ ] Backup system configured

### Docker Deployment

```bash
# Build image
docker build -t pysentry-waf:1.0.0 .

# Run container
docker run -d \
  --name pysentry-waf \
  -p 5000:5000 \
  -e MONGODB_URL=mongodb://mongo:27017 \
  -e REDIS_URL=redis://redis:6379 \
  -e SECRET_KEY=your-secret-key \
  --restart unless-stopped \
  pysentry-waf:1.0.0
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods -n pysentry-waf
kubectl logs -f deployment/pysentry-waf -n pysentry-waf
```

### Health Check

```bash
curl http://localhost:5000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "ml_model": "healthy"
  }
}
```

---

## Configuration Management

### Environment Variables

**Required**:
```bash
export MONGODB_URL="mongodb://user:pass@host:27017/waf_db"
export REDIS_URL="redis://host:6379/0"
export SECRET_KEY="your-256-bit-secret-key"
```

**Optional**:
```bash
export ENVIRONMENT="production"
export LOG_LEVEL="INFO"
export MAX_WORKERS=8
export CACHE_TTL=3600
export RATE_LIMIT=1000
```

### Configuration Files

Main config: `config/.env`

```ini
# Database
MONGODB_URL=mongodb://mongo:27017/waf_db
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=generate-with-openssl-rand-base64-32
JWT_EXPIRATION=3600

# Performance
MAX_WORKERS=8
CACHE_TTL=3600
BATCH_SIZE=100

# Monitoring
PROMETHEUS_PORT=9090
LOG_LEVEL=INFO
```

### Configuration Validation

```bash
# Validate configuration
python -m pysentry.core.config validate

# Show current configuration
python -m pysentry.core.config show
```

---

## Monitoring & Alerting

### Metrics Collection

**Prometheus Scrape Config**:
```yaml
scrape_configs:
  - job_name: 'pysentry-waf'
    static_configs:
      - targets: ['pysentry-waf:9090']
    scrape_interval: 15s
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `waf_requests_total` | Counter | Total requests processed |
| `waf_threats_detected_total` | Counter | Threats detected |
| `waf_blocked_requests_total` | Counter | Requests blocked |
| `waf_response_time_seconds` | Histogram | Response time distribution |
| `waf_cache_hit_ratio` | Gauge | Cache effectiveness |

### Alert Rules

**Critical Alerts** (PagerDuty):
```yaml
groups:
  - name: waf_critical
    rules:
      - alert: HighThreatRate
        expr: rate(waf_threats_detected_total[5m]) > 50
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High threat detection rate"
          
      - alert: WAFDown
        expr: up{job="pysentry-waf"} == 0
        for: 1m
        labels:
          severity: critical
```

### Log Aggregation

**ELK Stack Configuration**:
```yaml
# Filebeat
filebeat.inputs:
  - type: log
    paths:
      - /var/log/pysentry-waf/*.log
    json.keys_under_root: true
    
output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "pysentry-waf-%{+yyyy.MM.dd}"
```

### Grafana Dashboards

Import dashboard: `grafana/pysentry-waf-dashboard.json`

**Key Panels**:
- Request Rate (req/sec)
- Threat Detection Rate
- Block Rate
- Response Time (p50, p95, p99)
- Cache Hit Ratio
- Error Rate

---

## Backup & Recovery

### Database Backup

**MongoDB Backup** (Daily at 2 AM):
```bash
#!/bin/bash
# backup_mongodb.sh

BACKUP_DIR=/backups/mongodb
DATE=$(date +%Y%m%d)

mongodump \
  --uri="mongodb://user:pass@host:27017/waf_db" \
  --out="$BACKUP_DIR/backup-$DATE" \
  --gzip

# Retain 7 days
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;
```

**Redis Backup**:
```bash
# Configure in redis.conf
save 900 1
save 300 10
save 60 10000

# Manual backup
redis-cli --rdb /backups/redis/dump.rdb
```

### Restore Procedures

**MongoDB Restore**:
```bash
mongorestore \
  --uri="mongodb://user:pass@host:27017/waf_db" \
  --gzip \
  /backups/mongodb/backup-20241001
```

**Redis Restore**:
```bash
# Stop Redis
redis-cli shutdown

# Copy backup
cp /backups/redis/dump.rdb /var/lib/redis/

# Start Redis
redis-server
```

### Disaster Recovery

**RTO**: 15 minutes  
**RPO**: 1 hour

**DR Steps**:
1. Switch DNS to backup site
2. Restore latest database backup
3. Start services
4. Verify health checks
5. Monitor for 1 hour

---

## Troubleshooting

### High CPU Usage

**Symptoms**: CPU > 80% sustained

**Diagnosis**:
```bash
# Check processes
top -c

# Check WAF metrics
curl http://localhost:5000/api/v1/stats

# Check thread count
ps -eLf | grep pysentry | wc -l
```

**Resolution**:
1. Increase worker count: `MAX_WORKERS=16`
2. Enable caching if disabled
3. Scale horizontally (add more instances)

### High Memory Usage

**Symptoms**: Memory > 90%

**Diagnosis**:
```bash
# Memory usage by process
ps aux --sort=-%mem | head

# Python memory profiling
python -m memory_profiler src/pysentry/app.py
```

**Resolution**:
1. Reduce cache size: `CACHE_MAX_SIZE=1000000`
2. Reduce batch size: `BATCH_SIZE=50`
3. Restart service to clear memory leaks

### Database Connection Issues

**Symptoms**: "Connection refused" or "Timeout" errors

**Diagnosis**:
```bash
# Test MongoDB connection
mongo mongodb://host:27017/waf_db --eval "db.stats()"

# Test Redis connection
redis-cli -h host -p 6379 ping

# Check connection pool stats
curl http://localhost:5000/api/v1/stats | jq '.database'
```

**Resolution**:
1. Verify network connectivity
2. Check credentials
3. Increase connection pool: `DB_POOL_SIZE=50`
4. Check MongoDB/Redis logs

### Slow Response Times

**Symptoms**: Response time > 100ms

**Diagnosis**:
```bash
# Check metrics
curl http://localhost:5000/api/v1/metrics | grep response_time

# Enable slow query logging
export LOG_SLOW_QUERIES=true
export SLOW_QUERY_THRESHOLD=50
```

**Resolution**:
1. Enable caching: `CACHE_ENABLED=true`
2. Increase cache TTL: `CACHE_TTL=7200`
3. Optimize database queries
4. Add database indexes

---

## Performance Tuning

### Application Tuning

```bash
# Increase workers for CPU-bound tasks
export MAX_WORKERS=16

# Enable all caching layers
export CACHE_ENABLED=true
export CACHE_TTL=3600
export REDIS_CACHE_ENABLED=true

# Optimize batch processing
export BATCH_SIZE=200
export BATCH_TIMEOUT=5

# Connection pooling
export DB_POOL_SIZE=50
export DB_POOL_MIN=10
```

### Database Tuning

**MongoDB**:
```javascript
// Create indexes
db.threats.createIndex({ "detected_at": -1 })
db.threats.createIndex({ "type": 1, "severity": 1 })
db.threats.createIndex({ "source_ip": 1 })

// Enable profiling
db.setProfilingLevel(1, { slowms: 50 })
```

**Redis**:
```bash
# redis.conf
maxmemory 4gb
maxmemory-policy allkeys-lru
tcp-backlog 511
timeout 300
```

### Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 -H "Authorization: Bearer TOKEN" \
  http://localhost:5000/api/v1/analyze

# Using wrk
wrk -t12 -c400 -d30s http://localhost:5000/api/v1/health
```

**Target Benchmarks**:
- Throughput: > 10,000 req/sec
- Latency p95: < 10ms
- Latency p99: < 50ms

---

## Security Operations

### Security Hardening

1. **Network Security**:
   - Enable firewall (UFW/iptables)
   - Restrict port access
   - Use VPN for management

2. **Application Security**:
   - Rotate JWT keys monthly
   - Enable HTTPS only
   - Set secure headers
   - Disable debug mode

3. **Database Security**:
   - Enable authentication
   - Use TLS connections
   - Regular security patches
   - Audit logging

### Incident Response

**Security Incident Severity**:
- **SEV1**: System compromise, data breach
- **SEV2**: Unauthorized access attempt
- **SEV3**: DDoS attack
- **SEV4**: Configuration issue

**Response Steps**:
1. Identify and contain
2. Assess impact
3. Eradicate threat
4. Recover systems
5. Post-incident review

### Audit Logging

```bash
# Enable audit logging
export AUDIT_LOG_ENABLED=true
export AUDIT_LOG_PATH=/var/log/pysentry-waf/audit.log

# Review audit logs
tail -f /var/log/pysentry-waf/audit.log | jq '.'
```

---

## Maintenance Procedures

### Regular Maintenance

**Daily**:
- Review error logs
- Check disk space
- Monitor alert status

**Weekly**:
- Review performance metrics
- Analyze threat patterns
- Update threat intelligence

**Monthly**:
- Security patches
- Certificate renewal check
- Capacity planning review
- DR drill

### Update Procedure

```bash
# 1. Backup current deployment
kubectl get deployment pysentry-waf -o yaml > backup.yaml

# 2. Update image
kubectl set image deployment/pysentry-waf \
  pysentry-waf=pysentry-waf:1.1.0

# 3. Monitor rollout
kubectl rollout status deployment/pysentry-waf

# 4. Verify health
curl http://localhost:5000/api/v1/health

# 5. Rollback if needed
kubectl rollout undo deployment/pysentry-waf
```

---

## Runbooks

### Runbook: Service Not Responding

1. Check service status: `systemctl status pysentry-waf`
2. Check logs: `journalctl -u pysentry-waf -n 100`
3. Check port: `netstat -tulpn | grep 5000`
4. Restart service: `systemctl restart pysentry-waf`
5. Verify health: `curl http://localhost:5000/api/v1/health`

### Runbook: High False Positive Rate

1. Review recent threats: `curl http://localhost:5000/api/v1/threats?status=false_positive`
2. Identify patterns
3. Update ML model or rules
4. Test changes in staging
5. Deploy to production
6. Monitor for 24 hours

### Runbook: Database Migration

1. Schedule maintenance window
2. Backup current database
3. Test migration on copy
4. Put service in maintenance mode
5. Run migration
6. Verify data integrity
7. Restart service
8. Monitor for issues

---

## Support Escalation

**Tier 1**: Operations Team  
**Tier 2**: Development Team  
**Tier 3**: Security Team  

**Emergency Contact**: +1-555-0123  
**Email**: ops@pysentry-waf.com  
**Slack**: #pysentry-waf-ops

---

## Appendix

### Useful Commands

```bash
# View real-time logs
tail -f /var/log/pysentry-waf/app.log

# Check resource usage
docker stats pysentry-waf

# Export metrics
curl http://localhost:9090/metrics > metrics.txt

# Database stats
mongo --eval "db.stats()"

# Redis info
redis-cli info
```

### Quick Reference

| Task | Command |
|------|---------|
| Start service | `systemctl start pysentry-waf` |
| Stop service | `systemctl stop pysentry-waf` |
| Restart service | `systemctl restart pysentry-waf` |
| View logs | `journalctl -u pysentry-waf -f` |
| Health check | `curl http://localhost:5000/api/v1/health` |
| Metrics | `curl http://localhost:9090/metrics` |
