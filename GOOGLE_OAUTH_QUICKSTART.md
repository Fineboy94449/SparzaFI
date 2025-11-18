# Google OAuth Quick Start

## ⚡ 5-Minute Setup

### Step 1: Get Google Credentials (5 min)

1. Go to https://console.cloud.google.com/
2. Create new project → "SparzaFI"
3. Enable Google+ API
4. Create OAuth 2.0 credentials:
   - **Authorized redirect URI:** `http://localhost:5000/auth/google/callback`
5. Copy **Client ID** and **Client Secret**

### Step 2: Configure SparzaFI

Edit `run_app.sh` and uncomment these lines (lines 11-12):

```bash
export GOOGLE_CLIENT_ID="paste-your-client-id-here"
export GOOGLE_CLIENT_SECRET="paste-your-secret-here"
```

### Step 3: Run the App

```bash
./run_app.sh
```

### Step 4: Test

1. Open http://localhost:5000/login
2. Click the red "Google" button
3. Sign in with your Google account
4. Done! You're logged in

---

## ✅ What You Get

- **Users can sign in with Google** - No password needed
- **Auto-verified emails** - Google users are pre-verified
- **Profile pictures** - Synced from Google
- **Secure OAuth 2.0** - Industry-standard authentication

---

## 🔍 Check If It's Working

**Without credentials configured:**
- Google button will show error: "Google login is not configured"

**With credentials configured:**
- Google button redirects to Google sign-in page
- After login, user appears in Firebase `users` collection
- User has `google_id` field populated

---

## 📖 Full Documentation

See **GOOGLE_OAUTH_SETUP.md** for complete setup guide including:
- OAuth consent screen configuration
- Production deployment
- Security features
- Troubleshooting

---

**Status:** ✅ Code implemented, needs Google Cloud credentials
