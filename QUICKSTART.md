# 🚀 SparzaFI Sandbox - Quick Start

## Launch the Interactive CLI

Simply run:

```bash
cd /home/fineboy94449/Documents/SparzaFI
./sandbox.py
```

Or use the shorter command:

```bash
python3 sandbox.py
```

## What You'll See

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗██████╗  █████╗ ██████╗ ███████╗ █████╗        ║
║   ██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══███╔╝██╔══██╗       ║
║   ███████╗██████╔╝███████║██████╔╝  ███╔╝ ███████║       ║
║   ╚════██║██╔═══╝ ██╔══██║██╔══██╗ ███╔╝  ██╔══██║       ║
║   ███████║██║     ██║  ██║██║  ██║███████╗██║  ██║       ║
║   ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝       ║
║                                                           ║
║              🧪 SANDBOX MANAGER v1.0                      ║
║         Social Video Marketplace Platform                ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

Main Menu:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. 🚀 Start Sandbox (Local + ngrok)
  2. 🔧 Quick Setup (Database Only)
  3. 🔄 Reset Database with Demo Data
  4. 📊 View Database Stats
  5. 👥 Show Demo Accounts
  6. 🌐 Get Network URLs
  7. 📦 Install ngrok
  8. ☁️  Deploy to Cloud
  9. 🛠️  Advanced Options
  0. 🚪 Exit
```

## Features

### 1. 🚀 Start Sandbox
- One-click setup of complete testing environment
- Checks database
- Shows network URLs
- Displays demo accounts
- Optional: Start Flask server

### 2. 🔧 Quick Setup
- Creates fresh database
- Seeds initial data
- Optionally adds Thandi's Kitchen demo data

### 3. 🔄 Reset Database
- Removes old data
- Creates fresh database
- Repopulates with demo data

### 4. 📊 View Stats
```
Database Statistics:
────────────────────────────────────────────────────────────
  👥 Total Users: 10
  🛍️  Sellers: 3
  📦 Active Products: 15
  💰 Total Transactions: 19
  📦 Pending Orders: 4
  ⭐ Reviews: 5

  Top Seller: Thandi's Kitchen (R3740.00)
────────────────────────────────────────────────────────────
```

### 5. 👥 Demo Accounts
Shows all test credentials in a formatted list

### 6. 🌐 Network URLs
Displays:
- Localhost URLs
- Local network IP
- Instructions for sharing

### 7. 📦 Install ngrok
Automated ngrok installation with setup instructions

### 8. ☁️  Deploy to Cloud
Links to:
- Railway.app
- PythonAnywhere
- Render.com

### 9. 🛠️  Advanced Options
- Backup/Restore Database
- Export Demo Accounts
- Run Custom SQL Queries
- Check Dependencies

## Usage Examples

### First-Time Setup

```bash
# 1. Run the CLI
./sandbox.py

# 2. Choose option 2 (Quick Setup)
# This creates the database

# 3. Choose option 1 (Start Sandbox)
# This starts everything
```

### Daily Use

```bash
# Just run option 1
./sandbox.py
# Then choose: 1. Start Sandbox
```

### Share with Testers

```bash
# 1. Choose option 7 to install ngrok (first time only)
# 2. Choose option 1 to start sandbox
# 3. In another terminal: ngrok http 5000
# 4. Share the ngrok URL + option 5 (Demo Accounts)
```

### Reset for Clean Testing

```bash
./sandbox.py
# Choose: 3. Reset Database with Demo Data
```

### Check How Things Are Going

```bash
./sandbox.py
# Choose: 4. View Database Stats
```

## Tips

- **Colors not showing?** Make sure your terminal supports ANSI colors
- **Permission denied?** Run: `chmod +x sandbox.py`
- **Script not found?** Make sure you're in the SparzaFI directory
- **Need help?** All options have clear prompts and confirmations

## Advanced Features

### Backup Database
```bash
# In CLI: Advanced Options > Backup Database
# Creates: sparzafi_backup_YYYYMMDD_HHMMSS.db
```

### Run Custom SQL
```bash
# In CLI: Advanced Options > Run SQL Query
# Example: SELECT * FROM sellers;
```

### Export Accounts
```bash
# In CLI: Advanced Options > Export Demo Accounts
# Creates: DEMO_ACCOUNTS.txt
```

## Keyboard Shortcuts

- `Ctrl+C` - Exit CLI anytime
- `Enter` - Continue after viewing info
- `0` - Go back / Exit menus

## Troubleshooting

**"Please run from SparzaFI directory"**
```bash
cd /home/fineboy94449/Documents/SparzaFI
./sandbox.py
```

**"Database not found"**
- Choose option 2 (Quick Setup) to create it

**"ngrok not found"**
- Choose option 7 to install it

**Flask won't start**
- Check if port 5000 is already in use
- Kill existing Flask: `pkill -f "python3 app.py"`

## Pro Tips

1. **Use option 1 for demos** - It's the all-in-one starter
2. **Option 4 before demos** - Check data is loaded
3. **Option 5 to copy-paste** - Quick access to credentials
4. **Backup before resets** - Use Advanced Options > Backup
5. **Check dependencies** - Advanced Options > Check Dependencies

---

**That's it!** You now have a powerful CLI to manage your SparzaFI sandbox. 🎉

For more details, see:
- `SANDBOX_SETUP.md` - Full deployment guide
- `DEMO_ACCOUNTS.md` - Testing scenarios
- `README.md` - Platform overview
