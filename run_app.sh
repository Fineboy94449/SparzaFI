#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Set Firebase service account path
export FIREBASE_SERVICE_ACCOUNT=/home/fineboy94449/Documents/SparzaFI/firebase-service-account.json

# Google OAuth Configuration (optional - see GOOGLE_OAUTH_SETUP.md)
# Uncomment and fill in your credentials to enable Google login
# export GOOGLE_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
# export GOOGLE_CLIENT_SECRET="your-client-secret-here"

# Run Flask app
flask run --host=0.0.0.0 --port=5000
