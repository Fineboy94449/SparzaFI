#!/bin/bash
# SparzaFI Run Script
# This ensures the virtual environment Python is used with Firebase credentials

cd "$(dirname "$0")"
FIREBASE_SERVICE_ACCOUNT="./firebase-service-account.json" .venv/bin/python -m flask run --host=0.0.0.0 "$@"
