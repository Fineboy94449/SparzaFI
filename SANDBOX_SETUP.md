# 🧪 SparzaFI Sandbox Environment Setup

This guide shows you how to let people test your SparzaFI platform.

---

## 🚀 Quick Start (Easiest)

### Option 1: ngrok (Recommended for Testing)

**Install ngrok:**
```bash
# Download and install
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

**Setup:**
1. Sign up at https://dashboard.ngrok.com/signup (free)
2. Get your auth token from the dashboard
3. Authenticate:
```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

**Run your platform:**
```bash
# Terminal 1: Start Flask
cd /home/fineboy94449/Documents/SparzaFI
python3 app.py

# Terminal 2: Start ngrok
ngrok http 5000
```

**Share the URL:**
- You'll see something like: `https://abc123.ngrok.io`
- Share this with testers!
- They can access SparzaFI from anywhere in the world

---

## 🌐 Option 2: Local Network Access

If testers are on the same WiFi:

**Find your IP:**
```bash
hostname -I | awk '{print $1}'
```

**Share this URL:**
```
http://YOUR_IP:5000
```

Example: `http://192.168.8.6:5000`

---

## ☁️ Option 3: Deploy to Cloud (Production-Ready)

### Railway.app (Easiest Cloud Deploy)

1. **Sign up**: https://railway.app
2. **Install Railway CLI**:
```bash
npm install -g @railway/cli
```

3. **Deploy**:
```bash
cd /home/fineboy94449/Documents/SparzaFI
railway login
railway init
railway up
```

4. **Get your URL**: Railway will give you a public URL like:
   `https://sparzafi-production.up.railway.app`

### PythonAnywhere (Free Hosting)

1. Sign up: https://www.pythonanywhere.com
2. Upload your code via Git or web interface
3. Set up a web app (Flask, Python 3.10+)
4. Configure static files: `/static` → `/home/yourusername/SparzaFI/static`
5. Get URL: `https://yourusername.pythonanywhere.com`

### Render.com (Free Tier)

1. Sign up: https://render.com
2. Connect your GitHub repo (or upload)
3. Create new Web Service
4. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 app.py`
5. Deploy and get your URL

---

## 🔐 Sandbox Security Setup

### 1. Create Demo Accounts File

Create `DEMO_ACCOUNTS.md`:
```markdown
# SparzaFI Demo Accounts

## Admin
Email: admin@sparzafi.com
Password: adminpass

## Seller (Thandi's Kitchen)
Email: thandi@sparzafi.com
Password: sellerpass

## Buyer
Email: buyer1@test.com
Password: buyerpass

## Deliverer
Email: sipho.driver@sparzafi.com
Password: driverpass
```

### 2. Add Demo Mode Banner

Update `templates/base.html` to show a banner:
```html
<div style="background: #f59e0b; color: #000; padding: 0.5rem; text-align: center; font-weight: bold;">
    🧪 DEMO/SANDBOX MODE - Test data only
</div>
```

### 3. Auto-Reset Database (Optional)

Create a cron job to reset the database daily:
```bash
# Add to crontab
0 0 * * * cd /path/to/SparzaFI && rm sparzafi.db && python3 database_seed.py && python3 seed_thandi_data.py
```

---

## 📋 Testing Checklist for Users

Share this with your testers:

### As a Buyer:
- [ ] Browse seller videos on home page
- [ ] Like and follow sellers
- [ ] Add products to cart
- [ ] Complete checkout
- [ ] Track order delivery
- [ ] Leave a review

### As a Seller (Thandi's Kitchen):
- [ ] View dashboard statistics
- [ ] Confirm pending orders
- [ ] Mark orders ready for pickup
- [ ] Add new products
- [ ] Upload business videos
- [ ] Request withdrawal
- [ ] View analytics

### As a Deliverer:
- [ ] View available deliveries
- [ ] Accept delivery job
- [ ] Update delivery status
- [ ] Enter pickup/delivery codes
- [ ] Track earnings

---

## 🛠️ Monitoring Your Sandbox

### View Logs:
```bash
# If using ngrok
# Check Flask logs in terminal

# If on Railway/Render
# View logs in their dashboard
```

### Database Access:
```bash
# View database directly
sqlite3 sparzafi.db

# Common queries
SELECT COUNT(*) FROM users;
SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10;
SELECT name, balance FROM sellers;
```

### Reset Everything:
```bash
# Backup current database
cp sparzafi.db sparzafi_backup.db

# Fresh start
rm sparzafi.db
python3 database_seed.py
python3 seed_thandi_data.py
```

---

## 📊 Analytics & Feedback

### Track Usage:
```bash
# Count active sessions
sqlite3 sparzafi.db "SELECT COUNT(DISTINCT user_id) FROM transactions WHERE timestamp > datetime('now', '-1 hour')"

# Popular features
sqlite3 sparzafi.db "SELECT status, COUNT(*) FROM transactions GROUP BY status"
```

### Collect Feedback:
Create a Google Form or add a feedback button in the app.

---

## 🎯 Best Practices

1. **Always mention it's a sandbox**: Add banners, watermarks
2. **Don't use real payment info**: Only demo data
3. **Reset regularly**: Keep sandbox clean
4. **Monitor usage**: Check for abuse
5. **Provide demo accounts**: Don't make users sign up
6. **Document limitations**: List what works/doesn't work
7. **Be available**: Help testers if they get stuck

---

## 🚨 Troubleshooting

### ngrok URL not working?
- Check if Flask is running (port 5000)
- Verify ngrok is pointing to the right port
- Check firewall settings

### Testers can't login?
- Ensure email verification is disabled in sandbox
- Check if database exists: `ls -la sparzafi.db`
- Re-run seed scripts

### Slow performance?
- Use SQLite only for testing (< 10 users)
- For more users, switch to PostgreSQL
- Monitor server resources

---

## 📞 Getting Help

If you need help setting up:
1. Check Flask logs for errors
2. Test locally first (`http://localhost:5000`)
3. Verify database has demo data
4. Check ngrok/deployment logs

---

**Ready to go live?**
Share your sandbox URL and demo credentials with testers!

Example message:
```
🎉 Test SparzaFI Marketplace!

URL: https://your-url-here.ngrok.io

Demo Accounts:
• Buyer: buyer1@test.com / buyerpass
• Seller: thandi@sparzafi.com / sellerpass

Try:
- Browse videos on the home page
- Like/follow sellers
- Place an order
- Check out the seller dashboard

Feedback welcome! 🙏
```
