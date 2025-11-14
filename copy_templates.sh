#!/bin/bash

# SparzaFI Template Copy Script
# Copies all templates from bizzy-street-prototype and adapts them

SRC="/home/fineboy94449/Documents/bizzy-street-prototype/templates"
DEST="/home/fineboy94449/Documents/SparzaFI"

echo "🔄 Copying templates from bizzy-street-prototype to SparzaFI..."

# Copy auth templates
echo "📋 Copying auth templates..."
cp "$SRC/auth.html" "$DEST/auth/templates/" 2>/dev/null && echo "  ✅ auth.html"
cp "$SRC/kyc.html" "$DEST/auth/templates/" 2>/dev/null && echo "  ✅ kyc.html"

# Copy marketplace templates
echo "📋 Copying marketplace templates..."
cp "$SRC/index.html" "$DEST/marketplace/templates/" 2>/dev/null && echo "  ✅ index.html"
cp "$SRC/cart.html" "$DEST/marketplace/templates/" 2>/dev/null && echo "  ✅ cart.html"
cp "$SRC/checkout.html" "$DEST/marketplace/templates/" 2>/dev/null && echo "  ✅ checkout.html"
cp "$SRC/thank_you.html" "$DEST/marketplace/templates/" 2>/dev/null && echo "  ✅ thank_you.html"
cp "$SRC/transactions_explorer.html" "$DEST/marketplace/templates/" 2>/dev/null && echo "  ✅ transactions_explorer.html"

# Copy seller templates
echo "📋 Copying seller templates..."
cp "$SRC/seller_dashbord.html" "$DEST/seller/templates/seller_dashboard.html" 2>/dev/null && echo "  ✅ seller_dashboard.html"
cp "$SRC/seller_detail.html" "$DEST/seller/templates/" 2>/dev/null && echo "  ✅ seller_detail.html"
cp "$SRC/seller_setup.html" "$DEST/seller/templates/" 2>/dev/null && echo "  ✅ seller_setup.html"
cp "$SRC/edit_product.html" "$DEST/seller/templates/" 2>/dev/null && echo "  ✅ edit_product.html"

# Copy admin templates
echo "📋 Copying admin templates..."
cp "$SRC/admin_dashboard.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_dashboard.html"
cp "$SRC/admin_users.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_users.html"
cp "$SRC/admin_verification.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_verification.html"
cp "$SRC/admin_moderation.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_moderation.html"
cp "$SRC/admin_transactions_detailed.html" "$DEST/admin/templates/admin_transactions.html" 2>/dev/null && echo "  ✅ admin_transactions.html"
cp "$SRC/admin_audit_logs.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_audit_logs.html"
cp "$SRC/admin_analytics.html" "$DEST/admin/templates/" 2>/dev/null && echo "  ✅ admin_analytics.html"

# Copy user templates  
echo "📋 Copying user templates..."
cp "$SRC/user_profile.html" "$DEST/user/templates/" 2>/dev/null && echo "  ✅ user_profile.html"
cp "$SRC/user_settings.html" "$DEST/user/templates/" 2>/dev/null && echo "  ✅ user_settings.html"

echo ""
echo "✅ Template copying complete!"
echo ""
echo "⚠️  IMPORTANT: You must now update these templates:"
echo "   1. Change '{% extends \"base.html\" %}' to '{% extends \"shared/templates/base.html\" %}'"
echo "   2. Update url_for() calls to use blueprint routes (e.g., 'marketplace.index')"
echo "   3. Replace 'Bizzy Street' with 'SparzaFI'"
echo "   4. Update current_user to session.get('user')"
echo ""
echo "📖 See TEMPLATE_SETUP.md for detailed instructions"
