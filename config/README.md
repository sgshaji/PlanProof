# Configuration Files

This directory contains environment configuration templates for different deployment scenarios.

## Files

### Development
- **`.env.example`** - Development environment template (copy to `.env`)
  - Contains minimal required settings
  - Uses local/test credentials
  - Suitable for local development

### Production
- **`production.env.example`** - Production environment template
  - Comprehensive production settings
  - Security hardened
  - Includes monitoring, alerting, and backup configs
  - ⚠️ **Never commit with real credentials**

## Usage

### For Local Development
```bash
# Copy and customize for your environment
cp config/.env.example .env

# Edit .env with your local credentials
nano .env
```

### For Production Deployment
```bash
# Copy production template
cp config/production.env.example .env.production

# Replace ALL 'CHANGE_ME' placeholders with actual values
# Review security settings carefully

# Load in production (method depends on platform):

# Option 1: Docker/Docker Compose
docker-compose --env-file .env.production up

# Option 2: Azure App Service
# Upload as Application Settings in Azure Portal

# Option 3: Kubernetes
kubectl create secret generic planproof-config --from-env-file=.env.production
```

## Required Environment Variables

### Minimum Required (Development)
- `DATABASE_URL` - PostgreSQL connection string
- `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage
- `AZURE_DOCINTEL_ENDPOINT` + `AZURE_DOCINTEL_KEY` - Document Intelligence
- `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` - OpenAI API
- `AZURE_OPENAI_CHAT_DEPLOYMENT` - Deployment name

### Additional Required (Production)
- `JWT_SECRET_KEY` - Strong random key for authentication
- `API_KEYS` - Comma-separated API keys
- `AZURE_KEY_VAULT_NAME` - Key Vault for secrets
- `APPLICATIONINSIGHTS_CONNECTION_STRING` - Monitoring
- `SMTP_*` and `ALERT_EMAIL_*` - Email alerting
- `ALERT_WEBHOOK_URL` - Slack/Teams webhooks

## Security Best Practices

1. **Never Commit Secrets**
   ```bash
   # Ensure .env files are in .gitignore
   echo ".env" >> .gitignore
   echo ".env.*" >> .gitignore
   echo "!.env.example" >> .gitignore
   echo "config/*.env" >> .gitignore
   echo "!config/*.env.example" >> .gitignore
   ```

2. **Use Strong Passwords**
   - Minimum 16 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Use a password generator

3. **Rotate Secrets Regularly**
   - Quarterly rotation recommended
   - Immediate rotation if compromised
   - Update all environments

4. **Use Azure Key Vault in Production**
   - Store sensitive secrets in Key Vault
   - Use Managed Identity for access
   - Enable audit logging

5. **Restrict Access**
   - Limit who can view production configs
   - Use role-based access control
   - Audit access logs

## Configuration Validation

Test your configuration:
```bash
# Check database connection
python scripts/manual-tests/test_db_connection.py

# Run configuration validator
python -m planproof.config --validate

# Test Azure services
python scripts/smoke_test.py
```

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` format: `postgresql://user:pass@host:port/dbname`
- Check SSL requirements: Add `?sslmode=require` for production
- Test connection: `psql $DATABASE_URL`

### Azure Service Issues
- Verify endpoint URLs end with `/`
- Check API keys are valid and not expired
- Ensure services are in same region for best performance

### Environment Variable Not Loading
- Check file permissions: `chmod 600 .env`
- Verify file encoding: UTF-8 without BOM
- Check for extra whitespace in values
- Ensure no quotes around values (unless needed)

## Reference

For detailed documentation on each setting, see:
- [Configuration Guide](../docs/setup_guide.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Security Best Practices](../docs/SECURITY.md)
