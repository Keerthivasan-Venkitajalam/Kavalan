# GitHub Actions CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing and deployment of the Kavalan browser extension system.

## Workflows

### 1. CI Workflow (`ci.yml`)

**Trigger**: Push or Pull Request to `main` or `develop` branches

**Jobs**:

#### Extension CI
- Checkout code
- Setup Node.js 18
- Install dependencies
- Run ESLint linter
- Run TypeScript type checking
- Run Vitest unit and property-based tests
- Build extension with Vite
- Upload build artifacts

#### Backend CI
- Checkout code
- Setup Python 3.11
- Start PostgreSQL, MongoDB, Redis services
- Install dependencies
- Run Ruff linter
- Run MyPy type checker
- Initialize test databases
- Run pytest unit tests with coverage
- Run Hypothesis property-based tests
- Check 80% code coverage threshold
- Build Docker image
- Upload Docker image artifact

#### Integration Tests
- Run cross-service integration tests
- Test extension-backend communication
- Test parallel processing pipeline

#### Security Scan
- Run Trivy vulnerability scanner
- Upload results to GitHub Security

#### CI Summary
- Aggregate all job results
- Report overall CI status

**Requirements Validated**: 10.1, 10.2, 20.1

---

### 2. CD Workflow (`cd.yml`)

**Trigger**: 
- Automatic: After successful CI workflow on `main` branch
- Manual: `workflow_dispatch` with environment selection

**Jobs**:

#### Build and Push
- Build Docker images for backend services
- Push to GitHub Container Registry (ghcr.io)
- Generate Software Bill of Materials (SBOM)
- Tag images with commit SHA and branch name

#### Deploy to Staging
- **Automatic** after successful CI on `main`
- Deploy to AWS EKS cluster in Mumbai (ap-south-1)
- Use blue-green deployment strategy
- Run smoke tests on green deployment
- Switch traffic from blue to green
- Run post-deployment health checks
- Automatic rollback on failure

#### Deploy to Production
- **Manual approval required**
- Deploy to multiple regions:
  - Mumbai (ap-south-1)
  - Chennai (ap-southeast-1)
- Use blue-green deployment strategy
- Run smoke tests in each region
- Switch traffic gradually
- Monitor error rates for 5 minutes
- Notify via Slack on success/failure
- Automatic rollback on failure

#### Cleanup
- Scale down old blue deployments after successful green deployment
- Clean up old container images (keep last 10)

**Requirements Validated**: 10.3, 10.4, 10.5, 10.6, 10.7, 10.8

---

## Blue-Green Deployment Strategy

The CD workflow implements blue-green deployments to minimize downtime:

1. **Blue** = Current production version (serving traffic)
2. **Green** = New version being deployed
3. Deploy green alongside blue
4. Run smoke tests on green
5. Switch traffic from blue to green
6. Monitor for issues
7. Scale down blue if successful, rollback if failed

### Benefits
- Zero-downtime deployments
- Instant rollback capability
- Safe testing in production environment
- Reduced deployment risk

---

## Environment Variables

### CI Workflow

Required for testing:
- `DATABASE_URL`: PostgreSQL connection string
- `MONGODB_URL`: MongoDB connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET`: JWT signing key
- `ENCRYPTION_KEY`: AES-256 encryption key

### CD Workflow

Required secrets (configure in GitHub Settings → Secrets):
- `AWS_ACCESS_KEY_ID`: AWS credentials for EKS access
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `GITHUB_TOKEN`: Automatically provided by GitHub
- `SLACK_WEBHOOK_URL`: Slack webhook for deployment notifications

---

## Testing Strategy

### Unit Tests
- Test specific examples and edge cases
- Run on every commit
- Enforce 80% code coverage

### Property-Based Tests
- Test universal properties across all inputs
- Use Hypothesis (Python) and fast-check (TypeScript)
- Minimum 100 iterations per property
- Run on every commit

### Integration Tests
- Test cross-service communication
- Test database transactions
- Test parallel processing
- Run after unit tests pass

### Smoke Tests
- Run after deployment
- Verify critical endpoints
- Check system health
- Trigger rollback on failure

---

## Deployment Environments

### Staging
- **URL**: https://staging.kavalan.in
- **Region**: Mumbai (ap-south-1)
- **Cluster**: kavalan-staging-cluster
- **Auto-deploy**: Yes (on main branch)
- **Purpose**: Pre-production testing

### Production
- **URL**: https://kavalan.in
- **Regions**: 
  - Mumbai (ap-south-1) - Primary
  - Chennai (ap-southeast-1) - Secondary
- **Clusters**: 
  - kavalan-prod-mumbai
  - kavalan-prod-chennai
- **Auto-deploy**: No (manual approval required)
- **Purpose**: Live user traffic

---

## Manual Deployment

To manually trigger a deployment:

1. Go to **Actions** tab in GitHub
2. Select **CD - Deploy to Staging/Production** workflow
3. Click **Run workflow**
4. Select environment (staging or production)
5. Click **Run workflow** button

For production deployments:
- Requires manual approval in GitHub Environments
- Notifies team via Slack
- Monitors error rates post-deployment

---

## Rollback Procedure

### Automatic Rollback
- Triggered automatically if smoke tests fail
- Switches traffic back to blue deployment
- Notifies team via Slack

### Manual Rollback
If you need to manually rollback:

```bash
# Staging
kubectl patch service backend-service -n staging \
  -p '{"spec":{"selector":{"version":"blue"}}}'

# Production (Mumbai)
kubectl patch service backend-service -n production \
  -p '{"spec":{"selector":{"version":"blue"}}}' \
  --context kavalan-prod-mumbai

# Production (Chennai)
kubectl patch service backend-service -n production \
  -p '{"spec":{"selector":{"version":"blue"}}}' \
  --context kavalan-prod-chennai
```

---

## Monitoring

### CI Metrics
- Test pass rate
- Code coverage percentage
- Build duration
- Artifact size

### CD Metrics
- Deployment frequency
- Lead time for changes
- Mean time to recovery (MTTR)
- Change failure rate

### Post-Deployment
- Error rate monitoring (5 minutes)
- Response time monitoring
- Health check status
- Prometheus metrics

---

## Troubleshooting

### CI Failures

**Linter errors**:
```bash
# Extension
cd packages/extension
npm run lint -- --fix

# Backend
cd packages/backend
ruff check --fix app/ tests/
```

**Test failures**:
```bash
# Extension
npm run test

# Backend
pytest tests/ -v --tb=short
```

**Coverage below 80%**:
- Add more unit tests
- Focus on untested branches
- Check coverage report: `coverage report -m`

### CD Failures

**Smoke tests fail**:
- Check application logs: `kubectl logs -n <namespace> deployment/backend-green`
- Check service health: `kubectl get pods -n <namespace>`
- Verify environment variables: `kubectl describe deployment backend-green -n <namespace>`

**Rollback needed**:
- Automatic rollback should trigger
- If manual rollback needed, see Rollback Procedure above

**Image pull errors**:
- Verify GitHub Container Registry authentication
- Check image tag exists: `docker pull ghcr.io/<org>/<repo>/backend:<tag>`

---

## Best Practices

1. **Always run CI locally before pushing**:
   ```bash
   # Extension
   npm run lint && npm run type-check && npm run test
   
   # Backend
   ruff check app/ tests/ && pytest tests/
   ```

2. **Test staging before production**:
   - Deploy to staging first
   - Run manual tests
   - Verify metrics
   - Then deploy to production

3. **Monitor after deployment**:
   - Watch error rates in Grafana
   - Check logs in CloudWatch
   - Monitor user reports

4. **Keep deployments small**:
   - Deploy frequently
   - Small changes = easier rollback
   - Faster feedback loop

5. **Document breaking changes**:
   - Update CHANGELOG.md
   - Notify team in Slack
   - Update API documentation

---

## Security

### Image Scanning
- Trivy scans all Docker images
- Vulnerabilities reported to GitHub Security
- High/Critical vulnerabilities block deployment

### Secrets Management
- Never commit secrets to repository
- Use GitHub Secrets for sensitive data
- Rotate secrets regularly
- Use AWS Secrets Manager in production

### Access Control
- Production deployments require approval
- Only authorized users can approve
- All deployments logged and auditable

---

## Support

For issues with CI/CD:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Contact DevOps team
4. Create issue in repository

For deployment emergencies:
1. Trigger manual rollback
2. Notify on-call engineer
3. Check incident runbook
4. Post-mortem after resolution
