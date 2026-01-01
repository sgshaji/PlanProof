# VS Code Setup Guide for PlanProof

This guide will help you set up VS Code with all necessary extensions and settings for the PlanProof project.

## 🚀 Quick Setup (5 minutes)

### Step 1: Install VS Code Extensions

When you open this project in VS Code, you'll see a notification asking to install recommended extensions. Click **"Install All"**.

Or manually install by:
1. Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
2. Type: `Extensions: Show Recommended Extensions`
3. Click **"Install Workspace Recommended Extensions"**

### Step 2: Configure Database Connection

1. Copy `.vscode/settings.example.json` to `.vscode/settings.json`
2. Update the `password` field with the actual database password
3. Save the file

```bash
# On Windows PowerShell:
Copy-Item .vscode\settings.example.json .vscode\settings.json

# Then edit .vscode\settings.json and replace YOUR_PASSWORD_HERE
```

### Step 3: Set Up Python Environment

1. Open Terminal in VS Code: `` Ctrl+` ``
2. Create and activate virtual environment:

```powershell
# Create virtual environment
python -m venv .venv

# Activate it (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt
```

3. Select Python Interpreter:
   - Press `Ctrl+Shift+P`
   - Type: `Python: Select Interpreter`
   - Choose: `.venv\Scripts\python.exe`

### Step 4: Configure Environment Variables

1. Copy `.env.example` to `.env`
2. Fill in your Azure credentials and connection strings

```powershell
Copy-Item .env.example .env
# Then edit .env with your credentials
```

## 📦 Installed Extensions

### Required for Development
- **Python** - Python language support
- **Pylance** - Fast, feature-rich Python language server
- **Debugpy** - Python debugging
- **PostgreSQL** - Database management (2 extensions for compatibility)

### Recommended for Productivity
- **GitHub Copilot** - AI pair programmer
- **PDF Viewer** - View PDFs in VS Code
- **Rainbow CSV** - CSV file visualization
- **YAML** - YAML language support

### Azure Integration
- **Azure Bicep** - Infrastructure as code
- **Azure Containers** - Docker support
- **Azure Resource Groups** - Manage Azure resources

## 🔧 Key Settings Explained

### Python Configuration
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "python.testing.pytestEnabled": true,
  "python.formatting.provider": "black"
}
```

### Database Connections
Two PostgreSQL extensions are configured:
- **ckolkman.vscode-postgres** - For query execution
- **ms-ossdata.vscode-pgsql** - For database exploration

### Code Formatting
- **Black** formatter (88 character line limit)
- Format on save enabled
- Ruff linter for fast Python linting

## 📱 Sharing Setup with Others

### Option 1: Using This Repository (Recommended)
1. Clone/pull the repository - all settings are included
2. Install recommended extensions (Step 1 above)
3. Copy and configure `settings.json` (Step 2 above)
4. Set up Python environment (Step 3 above)

### Option 2: Manual Export/Import
If working outside this repository:

**Export extensions list:**
```powershell
code --list-extensions > my-extensions.txt
```

**Install extensions on another machine:**
```powershell
Get-Content my-extensions.txt | ForEach-Object { code --install-extension $_ }
```

### Option 3: VS Code Settings Sync
Enable Settings Sync in VS Code:
1. Click the gear icon (⚙️) → "Turn on Settings Sync"
2. Sign in with GitHub or Microsoft account
3. Select what to sync (Settings, Extensions, Keybindings)
4. On the other machine, sign in and sync

**Note:** Be careful with Settings Sync - it syncs passwords too! Use workspace settings instead.

## 🔒 Security Notes

### What's Committed to Git
✅ `.vscode/extensions.json` - Extension recommendations
✅ `.vscode/settings.example.json` - Template with no secrets
❌ `.vscode/settings.json` - Contains passwords (gitignored)

### What to Keep Private
- `.vscode/settings.json` - Contains database passwords
- `.env` - Contains Azure credentials
- Never commit these files!

## 🐛 Troubleshooting

### Extensions Not Installing
- Check internet connection
- Try installing one at a time manually
- Restart VS Code after installation

### Python Interpreter Not Found
- Ensure `.venv` folder exists: `Test-Path .venv`
- Recreate if needed: `python -m venv .venv`
- Restart VS Code after creating environment

### Database Connection Failed
- Verify credentials in `.vscode/settings.json`
- Check network connectivity to Azure
- Ensure PostgreSQL extensions are installed
- Try connecting via command line: `psql` command

### Copilot Not Working
- Sign in to GitHub: `Ctrl+Shift+P` → "GitHub Copilot: Sign In"
- Check subscription status
- Restart VS Code after signing in

## 📚 Additional Resources

- [VS Code Python Tutorial](https://code.visualstudio.com/docs/python/python-tutorial)
- [VS Code Settings Sync](https://code.visualstudio.com/docs/editor/settings-sync)
- [PostgreSQL Extension Guide](https://marketplace.visualstudio.com/items?itemName=ckolkman.vscode-postgres)

## ✨ Pro Tips

1. **Use Workspace Trust**: VS Code will ask to trust this workspace - click "Trust" to enable all features

2. **Keyboard Shortcuts**:
   - `Ctrl+Shift+P` - Command Palette
   - `` Ctrl+` `` - Toggle Terminal
   - `F5` - Start Debugging
   - `Ctrl+Shift+F` - Search in Files

3. **Integrated Terminal**: Use PowerShell terminal for best compatibility on Windows

4. **Database Explorer**: Use the PostgreSQL icon in the sidebar to browse database schema

5. **Copilot**: Press `Ctrl+I` for inline Copilot chat while coding

---

**Last Updated**: 2026-01-01
