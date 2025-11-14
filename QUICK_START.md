# 🚀 SparzaFI Quick Start Guide

## Running the Application

### Method 1: Flask CLI (Recommended) ⭐

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with Flask CLI
flask run
```

**Why Flask CLI?**
- ✅ Industry standard
- ✅ Better development experience
- ✅ Automatic reloading on code changes
- ✅ Environment variable support
- ✅ Access to Flask commands

### Method 2: Quick Start Script

```bash
# Make script executable (first time only)
chmod +x run.sh

# Run the script
./run.sh
```

### Method 3: Direct Python (Alternative)

```bash
source .venv/bin/activate
python3 app.py
```

---

## 🌐 Access Points

Once running, access SparzaFI at:

- **Main App:** http://localhost:5000
- **Admin:** http://localhost:5000/admin
- **API:** http://localhost:5000/api

**Network Access:** http://192.168.8.6:5000 (from other devices)

---

## 🔧 Flask CLI Commands

### Run Development Server
```bash
flask run
```

### Run on Custom Port
```bash
flask run --port 8000
```

### Run Without Debug Mode
```bash
FLASK_DEBUG=0 flask run
```

### Run with Public Access
```bash
flask run --host=0.0.0.0
```

### Database Commands (Future)
```bash
# Initialize database
flask db init

# Create migration
flask db migrate -m "description"

# Apply migration
flask db upgrade
```

---

## 🔐 Test Accounts

| Role | Email | Password | SPZ Balance |
|------|-------|----------|-------------|
| **Admin** | admin@sparzafi.com | adminpass | 50,000 SPZ |
| **Seller** | thandi@sparzafi.com | sellerpass | 3,500 SPZ |
| **Deliverer** | sipho.driver@sparzafi.com | driverpass | 2,100 SPZ |
| **Buyer** | buyer1@test.com | buyerpass | 1,500 SPZ |

---

## ⚙️ Environment Configuration

### .env File
The `.env` file contains all configuration:

```bash
# Flask Settings
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000

# Security
SECRET_KEY=your-secret-key
PASSWORD_SALT=sparzafi_salt_2025

# Database
DATABASE=sparzafi.db
```

### Change Port
Edit `.env`:
```bash
FLASK_RUN_PORT=8000
```

Then run:
```bash
flask run
```

### Disable Debug Mode
Edit `.env`:
```bash
FLASK_DEBUG=0
```

---

## 🛑 Stopping the Server

Press `CTRL+C` in the terminal

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use different port
flask run --port 8000
```

### Module Not Found
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Errors
```bash
# Reinitialize database
python3 database_seed.py
```

### Permission Denied (run.sh)
```bash
chmod +x run.sh
```

---

## 📊 Development Workflow

### 1. Start Development
```bash
source .venv/bin/activate
flask run
```

### 2. Make Code Changes
Flask automatically reloads when you save files

### 3. View Logs
All output appears in the terminal

### 4. Test Changes
Visit http://localhost:5000

### 5. Stop Server
Press `CTRL+C`

---

## 🔥 Hot Reload

Flask automatically reloads when you:
- ✅ Edit Python files (.py)
- ✅ Edit templates (.html)
- ❌ Change .env file (requires restart)
- ❌ Install new packages (requires restart)

---

## 🚀 Production Deployment

For production, use Gunicorn instead of Flask dev server:

```bash
# Install Gunicorn (already in requirements.txt)
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with gevent workers
gunicorn -w 4 -k gevent -b 0.0.0.0:5000 app:app
```

---

## 📝 Useful Commands

### Check Flask Version
```bash
flask --version
```

### List All Routes
```bash
flask routes
```

### Open Python Shell with App Context
```bash
flask shell
```

### Run Tests (when implemented)
```bash
pytest
```

---

## 🎯 Common Tasks

### Reset Database
```bash
rm sparzafi.db
python3 database_seed.py
```

### Clear Cache
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Generate New Secret Key
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 📖 Documentation

- **README.md** - Platform overview and features
- **API_DOCS.md** - API endpoints and usage
- **TEMPLATE_SETUP.md** - Template customization
- **REFINEMENT_SUMMARY.md** - Backend architecture
- **QUICK_START.md** - This file!

---

## 💡 Pro Tips

1. **Multiple Terminals:** Run app in one terminal, use another for commands
2. **VS Code:** Use integrated terminal for easy switching
3. **Logs:** Add `print()` statements for debugging (appears in terminal)
4. **Browser DevTools:** F12 to inspect frontend errors
5. **Network Tab:** Monitor API calls in browser DevTools

---

## ✅ Checklist for First Run

- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database initialized (auto-runs on first start)
- [ ] `.env` file created
- [ ] Run `flask run`
- [ ] Visit http://localhost:5000
- [ ] Login with test account
- [ ] Explore the platform!

---

## 🎉 You're All Set!

SparzaFI is now running with **Flask CLI**. Enjoy building your community marketplace and fintech platform!

**Quick Start:**
```bash
source .venv/bin/activate && flask run
```

**Visit:** http://localhost:5000

---

**Need Help?**
- Check Flask logs in terminal
- Review browser console (F12)
- Check `TROUBLESHOOTING.md` (coming soon)
- Restart server with `CTRL+C` then `flask run`
