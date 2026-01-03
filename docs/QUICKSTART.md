# 🚀 Quick Setup Guide - PlanProof Project

**Simple setup instructions for team members - takes just 10 minutes!**

## Super Simple Steps

### 1️⃣ Get the Code
- **Option A:** Ask your teammate to share the `PlanProof` folder  
- **Option B:** If using Git: `git clone <repository-url>`

### 2️⃣ Run the Magic Setup Script
Open PowerShell (Windows) or Terminal (Mac/Linux) in the PlanProof folder:

**Windows:**
```powershell
.\setup-dev.ps1
```

**Mac/Linux:**
```bash
chmod +x setup-dev.sh
./setup-dev.sh
```

**What this does:**
- ✅ Creates Python environment
- ✅ Installs all packages
- ✅ Creates config files for you

### 3️⃣ Add Your Credentials
The script created two files that need passwords:

**File 1: `.env`** (Azure credentials)
- Get credentials from your teammate
- **OR** copy their `.env` file

**File 2: `.vscode\settings.json`** (Database password)
- Add password on the line with `YOUR_PASSWORD_HERE`
- **OR** copy their `.vscode\settings.json` file

### 4️⃣ Open in VS Code
```powershell
code .
```

VS Code will show a popup: **"Install Recommended Extensions"**
- Click **"Install All"** ✅
- Wait 2-3 minutes for installation

### 5️⃣ Run the Application
In VS Code terminal (press `` Ctrl+` ``):
```powershell
python run_ui.py
```

Browser opens automatically → http://localhost:8501 🎉

---

## 🆘 If Something Goes Wrong

### Python Not Found?
```powershell
# Check if Python is installed
python --version

# Should show: Python 3.11.x or 3.12.x
# If not, install Python from python.org
```

### Can't Run PowerShell Script?
```powershell
# Run this first (one time only)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try again
.\setup-dev.ps1
```

### Virtual Environment Issues?
```powershell
# Delete and recreate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### Extensions Not Installing in VS Code?
- Restart VS Code
- Or install manually: `Ctrl+Shift+X` → search "Python" → Install

---

## 📋 What You're Getting

Your VS Code will have:
- ✅ Python support with intelligent code completion
- ✅ Database browser for PostgreSQL
- ✅ GitHub Copilot AI assistant (if you have access)
- ✅ PDF viewer built-in
- ✅ All the tools the team uses!

## 🔒 Important Files (Keep Private!)

**Never share or commit these:**
- `.env` - Contains Azure passwords
- `.vscode\settings.json` - Contains database password

**Safe to share:**
- Everything else in the project!

---

## 🎯 Daily Usage

Every time you work on the project:

1. **Open in VS Code**: `code .` (in PlanProof folder)
2. **Activate environment**: VS Code does this automatically!
3. **Run app**: `` Ctrl+` `` then `python run_ui.py`

That's it! 🚀

---

## 💡 Pro Tips

1. **Terminal Shortcut**: `` Ctrl+` `` (backtick key, left of number 1)
2. **Command Palette**: `Ctrl+Shift+P` (access everything in VS Code)
3. **File Search**: `Ctrl+P` (quickly open any file)
4. **Copilot Chat**: `Ctrl+I` (ask AI questions about code)

---

## 📞 Need Help?

1. Check [docs/VSCODE_SETUP.md](docs/VSCODE_SETUP.md) for detailed guide
2. Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
3. Ask a teammate! 😊

---

**You've got this! 💪**

> **Note:** This is a simplified quick-start guide. For detailed documentation, see [README.md](README.md) and the [docs/](docs/) folder.

