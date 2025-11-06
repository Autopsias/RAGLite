# CI/CD Secrets Checklist

**RAGLite - GitHub Actions Configuration**

This document lists all secrets and configuration required for the CI/CD pipeline.

---

## Current Status: No Secrets Required ✅

RAGLite's CI/CD pipeline currently runs entirely on **self-hosted runners** with **local services**. No external API keys or secrets are needed.

**Services:**
- **Qdrant**: Runs locally via Docker (`localhost:6333`)
- **PostgreSQL**: Runs locally via Docker (`localhost:5432`)
- **Test execution**: Uses local Python environment

---

## Future Secrets (Optional Enhancements)

As the pipeline evolves, you may need to configure these secrets:

### 1. **Slack Notifications** (Optional)

**When to add:** If you want CI failure notifications in Slack

**Secret Name:** `SLACK_WEBHOOK`

**How to configure:**
1. Create a Slack App at https://api.slack.com/apps
2. Enable "Incoming Webhooks"
3. Create a webhook for your desired channel
4. Copy the webhook URL
5. Add to GitHub:
   - Navigate to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `SLACK_WEBHOOK`
   - Value: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`

**Usage in workflow:**
```yaml
- name: Notify on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

### 2. **Codecov Token** (Optional)

**When to add:** If you want external coverage reporting/badges

**Secret Name:** `CODECOV_TOKEN`

**How to configure:**
1. Sign up at https://codecov.io/
2. Connect your GitHub repository
3. Copy the repository token
4. Add to GitHub:
   - Navigate to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `CODECOV_TOKEN`
   - Value: `<your-codecov-token>`

**Usage in workflow:**
```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    file: ./coverage.xml
```

---

### 3. **Anthropic API Key** (Optional)

**When to add:** If you want to test with real Claude API in CI

**Secret Name:** `ANTHROPIC_API_KEY`

**How to configure:**
1. Get API key from https://console.anthropic.com/
2. Add to GitHub:
   - Navigate to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-...`

**Usage in workflow:**
```yaml
- name: Run E2E tests with real LLM
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    pytest tests/e2e/ --real-llm
```

**⚠️ WARNING:** This will incur API costs. Use only for critical E2E validation.

---

### 4. **Mistral API Key** (Optional)

**When to add:** If you want to test with real Mistral API in CI

**Secret Name:** `MISTRAL_API_KEY`

**How to configure:**
1. Get API key from https://console.mistral.ai/
2. Add to GitHub:
   - Navigate to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `MISTRAL_API_KEY`
   - Value: `<your-mistral-api-key>`

**Usage in workflow:**
```yaml
- name: Run metadata extraction tests
  env:
    MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
  run: |
    pytest tests/integration/test_metadata_extraction.py
```

---

### 5. **Docker Hub Token** (Future - AWS Deployment)

**When to add:** If you deploy to AWS and need to push Docker images

**Secret Names:**
- `DOCKER_USERNAME`
- `DOCKER_TOKEN`

**How to configure:**
1. Create Docker Hub account
2. Generate access token: https://hub.docker.com/settings/security
3. Add to GitHub:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_TOKEN`: Your access token

**Usage in workflow:**
```yaml
- name: Login to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKER_USERNAME }}
    password: ${{ secrets.DOCKER_TOKEN }}
```

---

### 6. **AWS Credentials** (Future - Phase 4)

**When to add:** For Epic 4-5 (Production deployment)

**Secret Names:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

**How to configure:**
1. Create IAM user in AWS Console
2. Attach policy: `AmazonECS_FullAccess`, `AmazonS3_FullAccess`
3. Generate access keys
4. Add to GitHub:
   - `AWS_ACCESS_KEY_ID`: Your access key ID
   - `AWS_SECRET_ACCESS_KEY`: Your secret access key
   - `AWS_REGION`: `us-east-1` (or your preferred region)

**Usage in workflow:**
```yaml
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: ${{ secrets.AWS_REGION }}
```

---

## Environment Variables (Non-Secret)

These can be configured in workflow files directly (not secrets):

### Test Configuration

```yaml
env:
  # Use full 160-page PDF (default: false for speed)
  TEST_USE_FULL_PDF: "false"

  # Qdrant configuration
  QDRANT_HOST: localhost
  QDRANT_PORT: 6333

  # PostgreSQL configuration
  POSTGRES_HOST: localhost
  POSTGRES_PORT: 5432
  POSTGRES_DB: raglite
  POSTGRES_USER: raglite
  POSTGRES_PASSWORD: raglite  # OK for local testing
```

### Python Configuration

```yaml
env:
  # Python version (from .python-version or default)
  PYTHON_VERSION: "3.11"

  # Pytest configuration
  PYTEST_WORKERS: "4"  # Unit tests
  PYTEST_INTEGRATION_WORKERS: "1"  # Integration tests
```

---

## Security Best Practices

### ✅ DO:

1. **Never commit secrets to git**
   - Use `.env` files locally (gitignored)
   - Use GitHub Secrets for CI/CD
   - Rotate secrets regularly

2. **Use least privilege**
   - Grant minimum permissions needed
   - Create separate tokens for different purposes
   - Revoke tokens when no longer needed

3. **Encrypt sensitive data**
   - Use GitHub Encrypted Secrets
   - Never log secret values
   - Use `::add-mask::` in GitHub Actions if needed

4. **Audit access**
   - Review who has access to secrets
   - Monitor secret usage
   - Set up alerts for unauthorized access

### ❌ DON'T:

1. **Don't use production secrets in CI**
   - Use separate test accounts
   - Use sandboxed API keys
   - Limit rate/spend quotas

2. **Don't share secrets across projects**
   - Each project gets its own secrets
   - Use GitHub Organization secrets only for shared infrastructure

3. **Don't hardcode credentials**
   - No API keys in code
   - No passwords in workflows
   - No tokens in Dockerfiles

---

## Verification Checklist

After configuring secrets, verify:

- [ ] Secrets are added in GitHub: `Settings` → `Secrets and variables` → `Actions`
- [ ] Secret names match exactly (case-sensitive)
- [ ] Workflow references secrets correctly (`${{ secrets.SECRET_NAME }}`)
- [ ] Secrets are not logged in CI output
- [ ] Test run passes with secrets configured
- [ ] Access is restricted to necessary people only

---

## Troubleshooting

### Secret Not Working

**Symptom:** Workflow fails with "secret not found" or authentication errors

**Solutions:**
1. Check secret name spelling (case-sensitive)
2. Verify secret is in correct location:
   - Repository secrets: Available to all workflows
   - Environment secrets: Available to specific environments only
3. Re-create the secret (copy-paste errors common)
4. Check workflow YAML syntax: `${{ secrets.NAME }}` not `$secrets.NAME`

---

### Secret Leaked in Logs

**Symptom:** Secret value appears in CI logs

**Immediate Actions:**
1. **Revoke the secret immediately** (API key, token, etc.)
2. Generate a new secret
3. Update GitHub secret with new value
4. Review logs to understand how it leaked

**Prevention:**
```yaml
# Mask sensitive output
- name: Debug (safe)
  run: |
    echo "::add-mask::${{ secrets.API_KEY }}"
    echo "API Key: ${{ secrets.API_KEY }}"  # Will show as ***
```

---

## Current Configuration Status

**Last Updated:** 2025-11-05

| Secret | Required | Configured | Notes |
|--------|----------|------------|-------|
| SLACK_WEBHOOK | ❌ No | ❌ No | Optional - add for notifications |
| CODECOV_TOKEN | ❌ No | ❌ No | Optional - add for coverage badges |
| ANTHROPIC_API_KEY | ❌ No | ❌ No | Optional - only for real LLM testing |
| MISTRAL_API_KEY | ❌ No | ❌ No | Optional - only for metadata extraction testing |
| DOCKER_USERNAME | ❌ No | ❌ No | Future - AWS deployment (Epic 4-5) |
| DOCKER_TOKEN | ❌ No | ❌ No | Future - AWS deployment (Epic 4-5) |
| AWS_ACCESS_KEY_ID | ❌ No | ❌ No | Future - AWS deployment (Epic 4-5) |
| AWS_SECRET_ACCESS_KEY | ❌ No | ❌ No | Future - AWS deployment (Epic 4-5) |
| AWS_REGION | ❌ No | ❌ No | Future - AWS deployment (Epic 4-5) |

**Summary:** ✅ No secrets required for current pipeline. All services run locally.

---

## Questions?

- **GitHub Secrets Documentation**: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Security Hardening**: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- **Environment Protection Rules**: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment

For project-specific questions, see `docs/ci.md` or contact the team.
