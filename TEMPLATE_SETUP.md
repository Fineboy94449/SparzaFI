# SparzaFI Template Setup Guide

## ✅ Completed Setup

### 1. Base Template (DONE)
**Location:** `/shared/templates/base.html`

The base template includes:
- Modern dark theme with gradient headers
- Responsive navigation with search bar
- User profile dropdown (admin & regular users)
- Shopping cart icon with badge
- SPZ token balance display
- Fully responsive design (mobile, tablet, desktop)
- JavaScript for dropdowns and alerts
- Footer with company info

**Key Features:**
- Purple/blue gradient header (`#667eea` to `#764ba2`)
- Orange accent color (`#ff7a18`)
- Dark backgrounds for cards and forms
- Smooth animations and transitions
- Accessible ARIA labels

### 2. Folder Structure (DONE)
```
SparzaFI/
├── shared/templates/
│   └── base.html ✅
├── auth/templates/
├── marketplace/templates/
├── seller/templates/
├── admin/templates/
├── user/templates/
├── deliverer/templates/
└── static/
    ├── css/
    ├── js/
    ├── images/
    └── uploads/
```

---

## 📋 Next Steps: Copy Remaining Templates

### Source Location
All templates are in: `/home/fineboy94449/Documents/bizzy-street-prototype/templates/`

### Templates to Copy & Adapt

#### Authentication Templates (auth/templates/)
- [ ] `auth.html` - Login/Register form with tabs
- [ ] `kyc.html` - KYC verification form

#### Marketplace Templates (marketplace/templates/)
- [ ] `index.html` - Main marketplace feed
- [ ] `cart.html` - Shopping cart
- [ ] `checkout.html` - Checkout page
- [ ] `thank_you.html` - Order confirmation
- [ ] `transactions_explorer.html` - Transaction history

#### Seller Templates (seller/templates/)
- [ ] `seller_dashboard.html` - Seller dashboard
- [ ] `seller_detail.html` - Public seller profile
- [ ] `seller_setup.html` - Seller onboarding
- [ ] `edit_product.html` - Product management

#### Admin Templates (admin/templates/)
- [ ] `admin_dashboard.html` - Admin overview
- [ ] `admin_users.html` - User management
- [ ] `admin_verification.html` - Verification queue
- [ ] `admin_moderation.html` - Content moderation
- [ ] `admin_transactions.html` - Transaction monitoring
- [ ] `admin_audit_logs.html` - Audit logs
- [ ] `admin_analytics.html` - Analytics dashboard

#### User Templates (user/templates/)
- [ ] `user_profile.html` - User profile page
- [ ] `user_settings.html` - Account settings
- [ ] `wallet.html` - SPZ wallet dashboard

---

## 🔧 Template Adaptation Guide

When copying templates from bizzy-street-prototype, make these changes:

### 1. Extends Statement
```html
<!-- OLD -->
{% extends "base.html" %}

<!-- NEW -->
{% extends "shared/templates/base.html" %}
```

### 2. URL References
Update all `url_for()` calls to match SparzaFI blueprints:

```html
<!-- OLD -->
{{ url_for('feed') }}
{{ url_for('seller_page') }}
{{ url_for('admin_dashboard_enhanced') }}

<!-- NEW -->
{{ url_for('marketplace.index') }}
{{ url_for('seller.dashboard') }}
{{ url_for('admin.dashboard') }}
```

### 3. Blueprint URL Mapping

| Old Route | New Route | Description |
|-----------|-----------|-------------|
| `feed` | `marketplace.index` | Main marketplace |
| `cart_page` | `marketplace.cart` | Shopping cart |
| `checkout_page` | `marketplace.checkout` | Checkout |
| `transactions_explorer_page` | `marketplace.transactions_explorer` | Network |
| `signup_page` | `auth.login` | Login/Register |
| `logout` | `auth.logout` | Logout |
| `kyc_page` | `auth.kyc` | KYC verification |
| `seller_page` | `seller.dashboard` | Seller dashboard |
| `seller_detail` | `seller.detail` | Seller profile |
| `admin_dashboard_enhanced` | `admin.dashboard` | Admin dashboard |
| `admin_verification` | `admin.verification` | Verification |
| `admin_moderation` | `admin.moderation` | Moderation |
| `admin_transactions` | `admin.transactions` | Transactions |
| `admin_users` | `admin.users` | User management |
| `user_profile` | `user.profile` | User profile |
| `user_settings` | `user.settings` | Settings |

### 4. Branding Updates
- Replace "Bizzy Street" with "SparzaFI"
- Replace "bizzy" with "sparzafi" in IDs/classes
- Update logo references to `sparzafi-logo.png`

### 5. Session/User Access
```html
<!-- OLD -->
{% if current_user %}
    {{ current_user.email }}
{% endif %}

<!-- NEW -->
{% if session.get('user') %}
    {{ session.user.email }}
{% endif %}
```

---

## 🚀 Quick Copy Script

Use this bash script to copy all templates at once:

```bash
#!/bin/bash

# Set source and destination
SRC="/home/fineboy94449/Documents/bizzy-street-prototype/templates"
DEST="/home/fineboy94449/Documents/SparzaFI"

# Copy auth templates
cp "$SRC/auth.html" "$DEST/auth/templates/"
cp "$SRC/kyc.html" "$DEST/auth/templates/"

# Copy marketplace templates
cp "$SRC/index.html" "$DEST/marketplace/templates/"
cp "$SRC/cart.html" "$DEST/marketplace/templates/"
cp "$SRC/checkout.html" "$DEST/marketplace/templates/"
cp "$SRC/thank_you.html" "$DEST/marketplace/templates/"
cp "$SRC/transactions_explorer.html" "$DEST/marketplace/templates/"

# Copy seller templates
cp "$SRC/seller_dashbord.html" "$DEST/seller/templates/seller_dashboard.html"
cp "$SRC/seller_detail.html" "$DEST/seller/templates/"
cp "$SRC/seller_setup.html" "$DEST/seller/templates/"
cp "$SRC/edit_product.html" "$DEST/seller/templates/"

# Copy admin templates
cp "$SRC/admin_dashboard.html" "$DEST/admin/templates/"
cp "$SRC/admin_users.html" "$DEST/admin/templates/"
cp "$SRC/admin_verification.html" "$DEST/admin/templates/"
cp "$SRC/admin_moderation.html" "$DEST/admin/templates/"
cp "$SRC/admin_transactions_detailed.html" "$DEST/admin/templates/admin_transactions.html"
cp "$SRC/admin_audit_logs.html" "$DEST/admin/templates/"
cp "$SRC/admin_analytics.html" "$DEST/admin/templates/"

# Copy user templates
cp "$SRC/user_profile.html" "$DEST/user/templates/"
cp "$SRC/user_settings.html" "$DEST/user/templates/"

echo "✅ Templates copied! Now update the extends and url_for statements."
```

---

## 🎨 Styling Notes

The base.html template includes all necessary CSS. Additional page-specific styles can be added using:

```html
{% block extra_css %}
<style>
    /* Your custom styles here */
    .custom-class {
        color: var(--accent-color);
    }
</style>
{% endblock %}
```

### Available CSS Variables
```css
--primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
--accent-color: #ff7a18;
--dark-bg: #0f1724;
--darker-bg: #071024;
--card-bg: rgba(255, 255, 255, 0.05);
--border-color: rgba(255, 255, 255, 0.08);
--text-primary: #e6eef8;
--text-secondary: #94a3b8;
--success-color: #48bb78;
--error-color: #ff6b6b;
--warning-color: #f59e0b;
--radius: 14px;
--shadow: 0 6px 24px rgba(2, 6, 23, 0.6);
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Utility Classes
- `.card` - Card container with border and shadow
- `.btn` - Button base
- `.btn-primary` - Primary orange button
- `.btn-outline` - Outlined button
- `.btn-danger` - Red danger button
- `.btn-small` - Smaller button
- `.form-control` - Form input
- `.form-group` - Form field wrapper
- `.form-label` - Form label
- `.alert` - Alert message
- `.alert-success` / `.alert-error` / `.alert-warning` / `.alert-info`
- `.badge` - Badge/tag
- `.badge-success` / `.badge-warning` / `.badge-error`
- `.table-responsive` - Responsive table wrapper

---

## 🧪 Testing Templates

After copying templates, test each route:

```bash
# Start the app
source .venv/bin/activate
python3 app.py
```

Visit these URLs to test:
- http://localhost:5000/ - Marketplace index
- http://localhost:5000/auth/login - Login page
- http://localhost:5000/cart - Shopping cart
- http://localhost:5000/seller - Seller dashboard
- http://localhost:5000/admin - Admin dashboard
- http://localhost:5000/user/profile - User profile

---

## 📝 Template Structure Example

```html
{% extends "shared/templates/base.html" %}

{% block title %}Page Title - SparzaFI{% endblock %}

{% block extra_css %}
<style>
    /* Page-specific CSS */
</style>
{% endblock %}

{% block content %}
<div class="container">
    <h1>Page Heading</h1>

    <div class="card">
        <h2>Card Title</h2>
        <p>Card content</p>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // Page-specific JavaScript
</script>
{% endblock %}
```

---

## ✅ Summary

**Completed:**
- ✅ Base template with full styling and navigation
- ✅ Folder structure for all blueprints
- ✅ Static asset directories
- ✅ Logo placement (sparzafi-logo.png)

**Next Steps:**
1. Run the copy script above to copy all templates
2. Update `{% extends %}` statements in each template
3. Update `url_for()` calls to match blueprint routes
4. Update branding (Bizzy Street → SparzaFI)
5. Test each template by visiting its route

**Estimated Time:**
- Automated copy: 1 minute
- Manual updates: 30-60 minutes
- Testing: 15-30 minutes

---

**Total Progress:** Base template complete with professional dark theme, responsive design, and all utility classes ready to use!
