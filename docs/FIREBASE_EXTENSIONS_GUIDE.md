# Firebase Extensions Installation Guide

## Extensions Configured for SparzaFI

### Overview
Firebase Extensions are pre-built, open-source solutions that help you quickly add functionality to your app. All configuration files have been created and are ready for deployment.

---

## Configured Extensions

### 1. Trigger Email (firestore-send-email)
**Version**: 0.2.4
**Purpose**: Send transactional emails based on Firestore documents

**Use Cases for SparzaFI**:
- Order confirmations
- Delivery status updates
- Chat message notifications
- Password reset emails
- KYC verification notifications

**Configuration File**: `extensions/firestore-send-email.env`

**How to Configure**:
1. Choose an email provider:
   - **Gmail**: Create app password at https://myaccount.google.com/apppasswords
   - **SendGrid**: Get API key from https://sendgrid.com
   - **Mailgun**: Get API key from https://mailgun.com

2. Update `SMTP_CONNECTION_URI` in `extensions/firestore-send-email.env`:
   ```
   # Gmail
   SMTP_CONNECTION_URI=smtps://your-email@gmail.com:your-app-password@smtp.gmail.com:465

   # SendGrid
   SMTP_CONNECTION_URI=smtps://apikey:YOUR_SENDGRID_API_KEY@smtp.sendgrid.net:465

   # Mailgun
   SMTP_CONNECTION_URI=smtps://postmaster@YOUR_DOMAIN:YOUR_MAILGUN_API_KEY@smtp.mailgun.org:465
   ```

3. Update `DEFAULT_FROM` email address:
   ```
   DEFAULT_FROM=noreply@sparzafi.com
   ```

**How to Use in Code**:
```python
# Send email by creating a document in the 'mail' collection
email_doc = {
    'to': 'customer@example.com',
    'message': {
        'subject': 'Order Confirmation - SparzaFI',
        'text': f'Your order #{order_id} has been confirmed!',
        'html': f'<h1>Order Confirmed</h1><p>Order #{order_id}</p>'
    }
}
db.collection('mail').add(email_doc)
# Email will be sent automatically by the extension
```

---

### 2. Resize Images (storage-resize-images)
**Version**: 0.2.7
**Purpose**: Automatically resize uploaded images into multiple sizes

**Use Cases for SparzaFI**:
- Product images (thumbnail, medium, large)
- User profile pictures
- Seller verification photos
- Delivery proof images

**Configuration File**: `extensions/storage-resize-images.env`

**Configuration**:
- **Image Sizes**: 200x200 (thumbnail), 400x400 (medium), 800x800 (large)
- **Supported Formats**: JPEG, PNG, WebP
- **Output Directory**: `thumbnails/`
- **Original Images**: Preserved (not deleted)

**How It Works**:
1. User uploads image to Firebase Storage
2. Extension automatically creates 3 resized versions
3. Resized images saved in `thumbnails/{image_name}_200x200.{ext}`

**Access Resized Images**:
```python
# Original image
original_url = f"https://storage.googleapis.com/sparzafi-4edce.appspot.com/products/{product_id}/image.jpg"

# Thumbnail (200x200)
thumbnail_url = f"https://storage.googleapis.com/sparzafi-4edce.appspot.com/thumbnails/products/{product_id}/image_200x200.jpg"

# Medium (400x400)
medium_url = f"https://storage.googleapis.com/sparzafi-4edce.appspot.com/thumbnails/products/{product_id}/image_400x400.jpg"

# Large (800x800)
large_url = f"https://storage.googleapis.com/sparzafi-4edce.appspot.com/thumbnails/products/{product_id}/image_800x800.jpg"
```

---

### 3. Delete User Data (delete-user-data)
**Version**: 0.2.4
**Purpose**: Automatically delete user data when account is deleted (GDPR compliance)

**Use Cases for SparzaFI**:
- GDPR "Right to be Forgotten"
- User account deletion
- Data privacy compliance
- Clean up user-generated content

**Configuration File**: `extensions/delete-user-data.env`

**Data Deleted Automatically**:
- **Firestore Collections**:
  - `users/{UID}`
  - `transactions/{UID}`
  - `messages/{UID}`
  - `conversations/{UID}`
  - `notifications/{UID}`
  - `reviews/{UID}`

- **Storage Buckets**:
  - `users/{UID}/` - Profile data
  - `products/{UID}/` - Product images
  - `verification/{UID}/` - KYC documents

**How It Works**:
```python
# When you delete a user
from firebase_admin import auth

# Delete user from Firebase Auth
auth.delete_user(user_id)

# Extension automatically deletes all associated data:
# - Firestore documents
# - Storage files
# - Any other configured paths
```

**Manual Trigger**:
```python
# Alternatively, trigger deletion manually via callable function
from firebase_functions import https_fn

@https_fn.on_call()
def delete_my_account(req):
    user_id = req.auth.uid
    # Delete user (extension will handle data cleanup)
    auth.delete_user(user_id)
    return {'success': True}
```

---

## Installation Steps

### Option 1: Deploy via Firebase Console (Recommended for First-Time Setup)

1. **Go to Firebase Console Extensions**:
   ```
   https://console.firebase.google.com/project/sparzafi-4edce/extensions
   ```

2. **Install Each Extension**:
   - Click "Install Extension"
   - Search for extension name
   - Follow configuration wizard
   - Use values from `.env` files in `extensions/` directory

3. **Enable Billing**:
   - Extensions require Blaze (pay-as-you-go) plan
   - Go to: https://console.firebase.google.com/project/sparzafi-4edce/usage
   - Upgrade to Blaze plan (still has generous free tier)

### Option 2: Deploy via Firebase CLI (Requires Billing Enabled)

**Prerequisites**:
```bash
# Ensure you're logged in
firebase login

# Ensure billing is enabled (Blaze plan)
# Visit: https://console.firebase.google.com/project/sparzafi-4edce/usage
```

**Deploy All Extensions**:
```bash
cd "/home/fineboy94449/Documents/SparzaFI/SparzaFI main app"

# Deploy extensions (requires interactive configuration)
firebase ext:install firebase/firestore-send-email
firebase ext:install firebase/storage-resize-images
firebase ext:install firebase/delete-user-data
```

**Follow Interactive Prompts**:
- Extension will ask for configuration values
- Use values from `extensions/*.env` files
- Confirm installation

---

## Additional Recommended Extensions

### 4. Firestore Counter
**Extension ID**: `firebase/firestore-counter`

**Use Cases**:
- Product view counts
- Seller follower counts
- Total deliveries completed
- Order counts

**Installation**:
```bash
firebase ext:install firebase/firestore-counter
```

**Usage Example**:
```python
# Increment product view count
from firebase_admin import firestore

db = firestore.client()
product_ref = db.collection('products').document(product_id)

# Create counter document
counter_ref = db.collection('_counter_shards_').document(f'product_{product_id}_views')
counter_ref.set({
    'count': firestore.Increment(1)
})
```

---

### 5. Translate Text
**Extension ID**: `firebase/firestore-translate-text`

**Use Cases**:
- Multi-language product descriptions
- Translate chat messages
- Support multiple languages

**Installation**:
```bash
firebase ext:install firebase/firestore-translate-text
```

**Configuration**:
- Enable Cloud Translation API
- Select target languages (e.g., English, Afrikaans, Zulu, Xhosa)

---

### 6. BigQuery Export
**Extension ID**: `firebase/firestore-bigquery-export`

**Use Cases**:
- Business analytics
- Sales reporting
- User behavior analysis
- Transaction analytics

**Installation**:
```bash
firebase ext:install firebase/firestore-bigquery-export
```

**Configuration**:
- Select collections to export (transactions, products, users)
- BigQuery dataset created automatically
- Query data using BigQuery console

---

## Cost Estimates

### Free Tier Limits (Generous for Most Apps)

**Cloud Functions (Extensions use these)**:
- 2 million invocations/month FREE
- 400,000 GB-seconds compute time FREE
- 200,000 GHz-seconds CPU time FREE

**Cloud Storage (Image Resizing)**:
- 5 GB storage FREE
- 1 GB download/day FREE

**Email Sending (via SMTP)**:
- SendGrid: 100 emails/day FREE
- Mailgun: 5,000 emails/month FREE (first 3 months)
- Gmail: 500 emails/day (with app password)

**Estimated Monthly Cost** (with 10,000 users):
- Extensions: $0 - $5
- Image resizing: $0 - $2
- Email sending: $0 (free tier sufficient for most cases)

**Total**: ~$0-10/month for extensions

---

## Testing Extensions

### Test Email Extension
```python
# Create test email document
test_email = {
    'to': 'your-email@example.com',
    'message': {
        'subject': 'SparzaFI Extension Test',
        'text': 'If you receive this, the email extension is working!',
        'html': '<h1>Success!</h1><p>Email extension is working.</p>'
    }
}

db.collection('mail').add(test_email)

# Check extension logs
# firebase ext:logs firestore-send-email
```

### Test Image Resize
```python
# Upload test image to Storage
from firebase_admin import storage

bucket = storage.bucket()
blob = bucket.blob('test-images/sample.jpg')
blob.upload_from_filename('local-image.jpg')

# Wait ~10 seconds for extension to process
# Check for resized versions in /thumbnails/test-images/
```

### Test User Deletion
```python
# Create test user
from firebase_admin import auth

test_user = auth.create_user(
    email='test-delete@example.com',
    password='test123'
)

# Add test data
db.collection('users').document(test_user.uid).set({'name': 'Test User'})

# Delete user (extension should clean up data)
auth.delete_user(test_user.uid)

# Verify data deleted
user_doc = db.collection('users').document(test_user.uid).get()
print(user_doc.exists)  # Should be False
```

---

## Monitoring Extensions

### View Extension Logs
```bash
# View logs for specific extension
firebase ext:logs firestore-send-email

# View all function logs
firebase functions:log
```

### Firebase Console
```
https://console.firebase.google.com/project/sparzafi-4edce/extensions
```

- View extension status
- See invocation counts
- Check error rates
- Review configuration

---

## Troubleshooting

### Email Extension Not Sending

**Problem**: Emails not being delivered

**Solutions**:
1. Check SMTP credentials in extension configuration
2. Verify email provider allows SMTP connections
3. Check extension logs: `firebase ext:logs firestore-send-email`
4. Verify mail collection document structure
5. Check spam folder

### Image Resize Not Working

**Problem**: Resized images not appearing

**Solutions**:
1. Verify Firebase Storage is enabled
2. Check extension configuration (IMG_BUCKET, IMG_SIZES)
3. Ensure uploaded images are in supported format (JPEG/PNG/WebP)
4. Check extension logs: `firebase ext:logs storage-resize-images`
5. Wait up to 30 seconds for processing

### User Data Not Deleting

**Problem**: User data remains after account deletion

**Solutions**:
1. Verify extension is installed and enabled
2. Check FIRESTORE_PATHS and STORAGE_PATHS configuration
3. Ensure paths use {UID} placeholder correctly
4. Check extension logs: `firebase ext:logs delete-user-data`
5. Verify user was deleted from Firebase Auth (not just Firestore)

---

## Next Steps

1. **Enable Billing**: Upgrade to Blaze plan (required for extensions)
   - https://console.firebase.google.com/project/sparzafi-4edce/usage

2. **Install Extensions via Console** (Easiest):
   - https://console.firebase.google.com/project/sparzafi-4edce/extensions

3. **Configure Email Provider**:
   - Set up SendGrid/Mailgun/Gmail app password
   - Update `extensions/firestore-send-email.env`

4. **Test Each Extension**:
   - Send test email
   - Upload test image
   - Create/delete test user

5. **Integrate into App**:
   - Update email sending code to use 'mail' collection
   - Use resized image URLs in product display
   - Enable user account deletion

---

## Resources

- **Firebase Extensions Marketplace**: https://extensions.dev
- **Extension Documentation**: https://firebase.google.com/docs/extensions
- **Pricing Calculator**: https://firebase.google.com/pricing
- **Extension Support**: https://github.com/firebase/extensions

---

**Status**: Configuration files created ✅
**Next Action**: Enable billing and install via Firebase Console
**Estimated Setup Time**: 15-30 minutes

All extension configuration files are ready in the `extensions/` directory!
