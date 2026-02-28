# Grafana Dashboards for Kavalan

This directory contains Grafana dashboard configurations for monitoring the Kavalan threat detection system.

## Dashboards

### 1. Threat Detection Overview (`threat-detection-overview.json`)

Main operational dashboard showing:
- **Threat Detection Rate**: Real-time threats detected per second
- **Threats by Level**: Distribution of low/moderate/high/critical threats
- **End-to-End Latency**: p95 latency for complete processing pipeline
- **System Health Status**: API availability indicator
- **Threat Score Distribution**: Histogram of threat scores over time
- **Threats Timeline**: Time-series view of threats by severity level
- **Request Rate**: HTTP requests per second by endpoint
- **Error Rate**: Errors per second by type (with alerting)
- **Active WebSocket Connections**: Real-time connection count

**Use Case**: Primary dashboard for operations team to monitor threat detection effectiveness and system availability.

**Alerts**:
- High error rate (>0.1 errors/sec)

### 2. Service Performance (`service-performance.json`)

Detailed performance metrics for each service:

#### Audio Transcription Service
- Latency percentiles (p50, p95, p99)
- Task success rate gauge
- Tasks processed per second

#### Visual Analysis Service
- Latency percentiles (p50, p95, p99)
- Task success rate gauge
- Tasks processed per second

#### Liveness Detection Service
- Latency percentiles (p50, p95, p99)
- Task success rate gauge
- Tasks processed per second

#### Threat Fusion Service
- Latency percentiles (p50, p95, p99)
- Task success rate gauge
- Tasks processed per second

#### External API Performance
- API latency by service (Whisper, Gemini, MediaPipe)
- API success rate by service

**Use Case**: Performance engineering and optimization. Identify bottlenecks in individual services.

**SLA Targets**:
- Audio transcription: <500ms (p95)
- Visual analysis: <300ms (p95)
- Liveness detection: <200ms (p95)
- Threat fusion: <100ms (p95)

### 3. System Health (`system-health.json`)

Infrastructure and resource monitoring:

#### Queue & Workers
- Celery queue depth by queue name
- Active Celery workers count
- Worker utilization percentage

#### Database Performance
- Database operation latency (PostgreSQL, MongoDB)
- Database operations rate by operation type

#### Circuit Breakers
- Circuit breaker states (closed/open/half-open)
- Circuit breaker failure rates

#### Caching
- Cache hit rate gauge
- Cache operations (get/set, hit/miss)

#### HTTP Metrics
- Request latency heatmap by endpoint
- HTTP status codes distribution
- Task processing time heatmap

**Use Case**: Infrastructure monitoring and capacity planning. Detect resource exhaustion and scaling needs.

**Alerts**:
- High queue depth (>500 tasks)

## Setup

### Docker Compose Integration

Add Grafana and Prometheus to your `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: kavalan-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./packages/backend/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'
    networks:
      - kavalan-network

  grafana:
    image: grafana/grafana:latest
    container_name: kavalan-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=kavalan_admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - ./packages/backend/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./packages/backend/grafana/provisioning:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - kavalan-network

volumes:
  prometheus-data:
  grafana-data:

networks:
  kavalan-network:
    driver: bridge
```

### Prometheus Configuration

Create `packages/backend/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kavalan-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Access Dashboards

1. Start services:
   ```bash
   docker-compose up -d prometheus grafana
   ```

2. Access Grafana:
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `kavalan_admin`

3. Dashboards are automatically provisioned in the "Kavalan" folder

## Metrics Reference

### Threat Detection Metrics
- `kavalan_threats_detected_total{threat_level}` - Counter of threats by level
- `kavalan_threat_score` - Histogram of threat scores

### Latency Metrics
- `kavalan_audio_transcription_duration_seconds` - Audio processing time
- `kavalan_visual_analysis_duration_seconds` - Visual processing time
- `kavalan_liveness_detection_duration_seconds` - Liveness processing time
- `kavalan_threat_fusion_duration_seconds` - Fusion processing time
- `kavalan_end_to_end_latency_seconds` - Total pipeline latency

### Queue Metrics
- `kavalan_celery_queue_depth{queue_name}` - Tasks in queue
- `kavalan_celery_workers_active` - Active worker count
- `kavalan_celery_worker_utilization{worker_name}` - Worker utilization %
- `kavalan_celery_tasks_total{task_name, status}` - Task counts

### Database Metrics
- `kavalan_database_operations_total{database, operation, status}` - DB operation counts
- `kavalan_database_operation_duration_seconds{database, operation}` - DB latency

### External API Metrics
- `kavalan_external_api_calls_total{api_name, status}` - API call counts
- `kavalan_external_api_duration_seconds{api_name}` - API latency

### Circuit Breaker Metrics
- `kavalan_circuit_breaker_state{service}` - Circuit state (0=closed, 1=open, 2=half-open)
- `kavalan_circuit_breaker_failures_total{service}` - Failure counts

### Cache Metrics
- `kavalan_cache_operations_total{operation, result}` - Cache operations

### HTTP Metrics
- `kavalan_http_requests_total{method, endpoint, status}` - Request counts
- `kavalan_http_request_duration_seconds{method, endpoint}` - Request latency

### WebSocket Metrics
- `kavalan_websocket_connections_active` - Active connections
- `kavalan_websocket_messages_total{direction}` - Message counts

## Alerting

### Recommended Alert Rules

Create `packages/backend/prometheus/alerts.yml`:

```yaml
groups:
  - name: kavalan_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(kavalan_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: HighQueueDepth
        expr: kavalan_celery_queue_depth > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High queue depth in {{ $labels.queue_name }}"
          description: "Queue depth is {{ $value }} tasks"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(kavalan_end_to_end_latency_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High end-to-end latency"
          description: "p95 latency is {{ $value }}s (threshold: 2s)"

      - alert: LowWorkerCount
        expr: kavalan_celery_workers_active < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "No active workers"
          description: "Worker count is {{ $value }}"

      - alert: CircuitBreakerOpen
        expr: kavalan_circuit_breaker_state == 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.service }}"
          description: "Service {{ $labels.service }} is failing"

      - alert: LowCacheHitRate
        expr: sum(rate(kavalan_cache_operations_total{operation="get", result="hit"}[5m])) / sum(rate(kavalan_cache_operations_total{operation="get"}[5m])) < 0.5
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

## Customization

### Adding Custom Panels

1. Edit dashboard JSON files directly, or
2. Use Grafana UI to modify dashboards (changes persist if `allowUiUpdates: true`)
3. Export modified dashboards and save to this directory

### Modifying Refresh Rates

Edit the `refresh` field in dashboard JSON:
- `"5s"` - 5 second refresh
- `"10s"` - 10 second refresh
- `"30s"` - 30 second refresh
- `"1m"` - 1 minute refresh

### Adjusting Time Ranges

Edit the `time` field in dashboard JSON:
```json
"time": {
  "from": "now-1h",  // Last 1 hour
  "to": "now"
}
```

Options: `now-5m`, `now-15m`, `now-30m`, `now-1h`, `now-6h`, `now-24h`, `now-7d`

## Troubleshooting

### Dashboards Not Appearing

1. Check Grafana logs:
   ```bash
   docker logs kavalan-grafana
   ```

2. Verify provisioning configuration:
   ```bash
   docker exec kavalan-grafana cat /etc/grafana/provisioning/dashboards/dashboards.yml
   ```

3. Restart Grafana:
   ```bash
   docker-compose restart grafana
   ```

### No Data in Panels

1. Verify Prometheus is scraping metrics:
   - Open http://localhost:9090
   - Go to Status > Targets
   - Check `kavalan-api` target is UP

2. Test metrics endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. Check Prometheus data source in Grafana:
   - Configuration > Data Sources > Prometheus
   - Click "Test" button

### High Memory Usage

Reduce Prometheus retention:
```yaml
command:
  - '--storage.tsdb.retention.time=30d'  # Reduce from 90d
```

## Best Practices

1. **Monitor the Monitors**: Set up alerts for Prometheus and Grafana availability
2. **Regular Reviews**: Review dashboards weekly to identify trends
3. **Capacity Planning**: Use 7-day and 30-day views to plan scaling
4. **Alert Fatigue**: Tune alert thresholds to reduce false positives
5. **Documentation**: Document any custom panels or modifications
6. **Backup**: Regularly backup Grafana dashboards and Prometheus data

## References

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
