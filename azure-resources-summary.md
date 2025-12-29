# Azure Resources Provisioning Summary

## ✅ Successfully Provisioned Resources

### Resource Group
- **Name:** `planproof-dev-rg`
- **Location:** UK South
- **Subscription:** Azure subscription 1 (3fb131c0-46e0-4f4c-ad41-166eac0adaf4)

### Azure Blob Storage
- **Account Name:** `planproofdevstg86723`
- **Containers Created:**
  - `inbox`
  - `artefacts`
  - `logs`
- **Connection String:** Stored in `.env` file

### PostgreSQL Flexible Server
- **Server Name:** `planproof-dev-pgflex-8016`
- **Version:** PostgreSQL 14
- **SKU:** Standard_B1ms (Burstable)
- **Location:** UK South
- **Admin User:** `pgadmin`
- **Admin Password:** `Va0PrCJQ4Y7wc29EyXRl` ⚠️ **Keep this secure!**
- **Database:** `planning_validation`
- **Firewall Rule:** IP `111.92.22.57` allowed (AllowDevMachine)
- **PostGIS:** Enabled at server level ✅
- **Note:** PostGIS extension needs to be enabled in the database itself:
  ```sql
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS postgis_topology;
  ```

### Azure OpenAI
- **Service Name:** `planproof-dev-aoai-7542`
- **Endpoint:** `https://planproof-dev-aoai-7542.openai.azure.com/` (resource-specific format - recommended)
- **API Key:** Stored in `.env` file
- **Status:** ✅ Created
- **Note:** You'll need to deploy a model (e.g., `gpt-4o-mini`) via Azure Portal or CLI

### Azure Document Intelligence
- **Service Name:** `planproof-dev-docint-3619`
- **Endpoint:** `https://uksouth.api.cognitive.microsoft.com/`
- **API Key:** Stored in `.env` file
- **Status:** ✅ Created and ready to use

## 📝 Configuration File

All connection strings and credentials have been saved to `.env` file in the project root.

## ⚠️ Important Notes

1. **PostgreSQL Password:** The admin password is stored in `.env`. Make sure this file is in `.gitignore` and never commit it to version control.

2. **PostGIS Extension:** While PostGIS is enabled at the server level, you need to enable it in the database when you first connect:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS postgis_topology;
   ```

3. **OpenAI Model Deployment:** The Azure OpenAI service is created, but you need to deploy a model (e.g., `gpt-4o-mini`) before you can use it. This can be done via:
   - Azure Portal: Navigate to your OpenAI resource → Model deployments
   - Azure CLI: `az cognitiveservices account deployment create --name planproof-dev-aoai-7542 --resource-group planproof-dev-rg --deployment-name gpt-4o-mini --model-name gpt-4o-mini --model-version "2024-07-18" --model-format OpenAI`

4. **Firewall Rules:** PostgreSQL firewall is currently configured to allow your current IP (`111.92.22.57`). If your IP changes, you'll need to update the firewall rule.

5. **Cost Management:** The PostgreSQL server can be stopped/started to save costs:
   ```powershell
   az postgres flexible-server stop --resource-group planproof-dev-rg --name planproof-dev-pgflex-8016
   az postgres flexible-server start --resource-group planproof-dev-rg --name planproof-dev-pgflex-8016
   ```

## 🔐 Security Recommendations

1. Rotate passwords regularly
2. Consider using Azure Key Vault for storing secrets in production
3. Restrict PostgreSQL firewall rules to only necessary IPs
4. Enable private endpoints for production environments
5. Regularly review and audit access logs

## 📊 Resource Costs (Approximate)

- **PostgreSQL Flexible Server (B1ms):** ~$0.019/hour (can be stopped when not in use)
- **Azure Blob Storage:** Pay per use (first 5GB free)
- **Azure OpenAI:** Pay per use (depends on model and usage)
- **Document Intelligence:** Pay per use (first 500 pages/month free on S0 tier)

