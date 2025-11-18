# Google OAuth Setup Guide for SparzaFI

## Overview

This guide will help you set up Google OAuth authentication for SparzaFI, allowing users to sign in with their Google accounts.

---

## ✅ What's Already Implemented

- ✅ Backend OAuth routes (`/auth/google` and `/auth/google/callback`)
- ✅ Google OAuth packages installed (`google-auth-oauthlib`)
- ✅ Frontend "Sign in with Google" buttons on login and signup pages
- ✅ User creation/login flow for Google accounts
- ✅ Automatic email verification for Google users
- ✅ Profile picture synchronization from Google

---

## 🔧 Setup Steps

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: **"SparzaFI"** (or your preferred name)
4. Click **"Create"**

### 2. Enable Google+ API

1. In the Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google+ API"** or **"Google Identity"**
3. Click on it and click **"Enable"**

### 3. Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. Choose **"External"** (for public users) or **"Internal"** (if G Suite organization)
3. Click **"Create"**

**Fill in the required fields:**
- **App name:** SparzaFI
- **User support email:** Your email address
- **App logo:** (Optional) Upload SparzaFI logo
- **Application home page:** `http://localhost:5000` (development) or your domain (production)
- **Authorized domains:** Add your domain (e.g., `sparzafi.com`)
- **Developer contact information:** Your email address

4. Click **"Save and Continue"**

**Scopes:**
5. Click **"Add or Remove Scopes"**
6. Select these scopes:
   - `email` - View your email address
   - `profile` - See your personal info
   - `openid` - Associate you with your personal info on Google

7. Click **"Update"** → **"Save and Continue"**

**Test users (for development):**
8. Add your test email addresses
9. Click **"Save and Continue"**
10. Review and click **"Back to Dashboard"**

### 4. Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. Choose **"Web application"**

**Configure:**
- **Name:** SparzaFI Web Client
- **Authorized JavaScript origins:**
  - Development: `http://localhost:5000`
  - Production: `https://yourdomain.com`

- **Authorized redirect URIs:**
  - Development: `http://localhost:5000/auth/google/callback`
  - Production: `https://yourdomain.com/auth/google/callback`

4. Click **"Create"**

5. **Save your credentials:**
   - Copy the **Client ID**
   - Copy the **Client Secret**

---

## 🔐 Configure Environment Variables

Add these to your environment or `.env` file:

```bash
# Google OAuth Configuration
export GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"
```

**For development**, add to `run_app.sh`:

```bash
#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set Firebase service account path
export FIREBASE_SERVICE_ACCOUNT=/home/fineboy94449/Documents/SparzaFI/firebase-service-account.json

# Google OAuth credentials
export GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret-here"

# Run Flask app
flask run --host=0.0.0.0 --port=5000
```

**For production**, set environment variables in your hosting platform:
- Heroku: `heroku config:set GOOGLE_CLIENT_ID=...`
- AWS/Azure: Set in environment configuration
- Docker: Add to `docker-compose.yml` or `.env` file

---

## 🧪 Testing

### 1. Start the Application

```bash
./run_app.sh
```

### 2. Test Google Login

1. Open browser to `http://localhost:5000/login`
2. Click the **"Google"** button (red button with 🔴 icon)
3. You should be redirected to Google's login page
4. Sign in with your Google account
5. Grant permissions (email, profile)
6. You'll be redirected back to SparzaFI and logged in

### 3. Verify User Creation

Check Firebase Console → Firestore → `users` collection

You should see a new user with:
- ✅ `google_id` - Google's unique ID for the user
- ✅ `email` - User's Gmail address
- ✅ `full_name` - Name from Google account
- ✅ `profile_picture` - Google profile picture URL
- ✅ `email_verified: true` - Automatically verified
- ✅ `password_hash: ""` - Empty (Google-only account)

---

## 🔍 How It Works

### OAuth Flow

1. **User clicks "Sign in with Google"**
   - Frontend redirects to `/auth/google`

2. **Backend initiates OAuth flow**
   - Generates authorization URL with Google
   - Stores CSRF state token in session
   - Redirects user to Google login page

3. **User authenticates with Google**
   - User signs in to their Google account
   - Google shows consent screen (permissions)
   - User approves access

4. **Google redirects back to app**
   - Callback URL: `/auth/google/callback`
   - Includes authorization code in query params

5. **Backend exchanges code for tokens**
   - Verifies CSRF state token
   - Exchanges authorization code for ID token
   - Verifies ID token with Google
   - Extracts user information (email, name, picture)

6. **User creation/login**
   - **Existing user:** Updates Google info, logs in
   - **New user:** Creates account in Firebase, logs in
   - Sets session and redirects to dashboard

---

## 🔒 Security Features

- ✅ **CSRF Protection:** Uses state parameter to prevent cross-site attacks
- ✅ **Token Verification:** Validates ID tokens with Google servers
- ✅ **Secure Session:** Uses Flask's secure session management
- ✅ **HTTPS Required:** Google OAuth requires HTTPS in production
- ✅ **Scope Limiting:** Only requests necessary permissions (email, profile)

---

## 🚀 Production Deployment

### Before Going Live:

1. **Update OAuth Consent Screen**
   - Change from "Testing" to "In Production"
   - Submit for Google verification if needed

2. **Update Redirect URIs**
   - Add your production domain
   - Remove localhost URIs

3. **Enable HTTPS**
   - Google OAuth requires HTTPS in production
   - Use Let's Encrypt or your hosting provider's SSL

4. **Set Environment Variables**
   - Configure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
   - Never commit credentials to version control

5. **Test Production Flow**
   - Test login with multiple Google accounts
   - Verify new user creation
   - Test existing user login

---

## 🐛 Troubleshooting

### Error: "Google login is not configured"

**Solution:** Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-secret"
```

### Error: "redirect_uri_mismatch"

**Solution:** The redirect URI in your Google Cloud Console must exactly match:
- Development: `http://localhost:5000/auth/google/callback`
- Production: `https://yourdomain.com/auth/google/callback`

Check:
1. Protocol (http vs https)
2. Domain/IP
3. Port number
4. Path (`/auth/google/callback`)

### Error: "Invalid OAuth state"

**Solution:** CSRF protection failed. Clear your session and try again:
1. Clear browser cookies for the site
2. Restart Flask app
3. Try login again

### Error: "Access blocked: This app's request is invalid"

**Solution:** OAuth consent screen not configured properly:
1. Complete all required fields in OAuth consent screen
2. Add authorized domains
3. Publish app (change from Testing to Production if needed)

### Google Button Doesn't Work

**Check:**
1. JavaScript console for errors
2. Verify `url_for('auth.google_login')` generates correct URL
3. Check that OAuth routes are registered with Flask

---

## 📊 User Data Mapping

| Google Field | SparzaFI Field | Notes |
|-------------|----------------|-------|
| `sub` | `google_id` | Unique Google user ID |
| `email` | `email` | Primary email |
| `name` | `full_name` | Display name |
| `picture` | `profile_picture` | Avatar URL |
| `email_verified` | `email_verified` | Always `true` for Google users |

---

## 🔄 Linking Existing Accounts

If a user already has a SparzaFI account with email/password and then signs in with Google using the same email:

- ✅ The existing account is linked automatically
- ✅ `google_id` is added to their account
- ✅ They can now use either login method
- ✅ Their data is preserved

---

## 📝 Next Steps (Optional)

### Add More OAuth Providers

- Facebook Login
- Apple Sign In
- Microsoft Account
- GitHub (for developers)

### Enhanced Profile Management

- Allow users to unlink Google account
- Profile picture upload override
- Multiple login methods per account

### Analytics

- Track Google vs email signups
- Monitor OAuth conversion rates
- A/B test OAuth button placement

---

## 📚 Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Flask-OAuthlib Documentation](https://flask-oauthlib.readthedocs.io/)

---

**Last Updated:** 2025-11-18

**Status:** ✅ Ready for Configuration
