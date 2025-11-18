"""
Admin Routes - Migrated to Firebase
Dashboard, verification, moderation, and compliance
"""

from flask import render_template, redirect, url_for, session, request, abort, jsonify, make_response
from flask import current_app as app
from shared.utils import admin_required
from shared.components import render_chart_data
from . import admin_bp
import csv
from io import StringIO
from datetime import datetime

# Firebase imports
from firebase_db import (
    seller_service,
    get_product_service,
    transaction_service,
    get_user_service,
    verification_submission_service,
    seller_badge_service
)
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard_enhanced():
    """Admin Analytics Dashboard"""
    db = get_firestore_db()
    product_service = get_product_service()

    # Get summary statistics
    # Count sellers
    total_sellers = len(seller_service.get_all_sellers())

    # Count active products
    all_products = product_service.get_all()
    total_products = sum(1 for p in all_products if p.get('is_active', True))

    # Count transactions
    all_transactions = db.collection('transactions').stream()
    total_transactions = sum(1 for _ in all_transactions)

    # Calculate total revenue and commission
    completed_trans = db.collection('transactions').where(
        filter=FieldFilter('status', 'in', ['COMPLETED', 'DELIVERED'])
    ).stream()

    total_revenue = 0.0
    platform_commission = 0.0

    for doc in completed_trans:
        trans = doc.to_dict()
        total_revenue += float(trans.get('total_amount', 0))
        platform_commission += float(trans.get('platform_commission', 0))

    summary = {
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_transactions': total_transactions,
        'total_revenue': f"R{total_revenue:.2f}",
        'platform_commission': f"R{platform_commission:.2f}"
    }

    # Get recent transactions (last 15)
    recent_trans = db.collection('transactions').order_by(
        'created_at', direction='DESCENDING'
    ).limit(15).stream()

    transactions = []
    for doc in recent_trans:
        trans = {**doc.to_dict(), 'id': doc.id}

        # Get user email
        if trans.get('user_id'):
            user = get_user_service().get(trans['user_id'])
            trans['user_email'] = user.get('email', '') if user else ''

        # Get seller name
        if trans.get('seller_id'):
            seller = seller_service.get(trans['seller_id'])
            trans['seller_name'] = seller.get('name', '') if seller else ''

        trans['display_amount'] = f"R{float(trans.get('total_amount', 0)):.2f}"
        transactions.append(trans)

    # Get all active products with seller info
    active_products = [p for p in all_products if p.get('is_active', True)]

    products = []
    for product in active_products[:50]:  # Limit to 50
        # Get seller info
        if product.get('seller_id'):
            seller = seller_service.get(product['seller_id'])
            product['seller_name'] = seller.get('name', '') if seller else ''
            product['handle'] = seller.get('handle', '') if seller else ''
            product['verification_status'] = seller.get('verification_status', '') if seller else ''

        product['product_name'] = product.get('name', '')
        product['display_price'] = f"R{float(product.get('price', 0)):.2f}"
        products.append(product)

    # Sort products by created_at
    products.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return render_template('admin_dashboard.html',
        summary=summary,
        transactions=transactions,
        products=products
    )


@admin_bp.route('/verification')
@admin_required
def admin_verification():
    """Seller Verification Dashboard"""

    # Get pending verification submissions
    pending = verification_submission_service.get_pending_submissions()

    # Enrich with user and seller info
    for submission in pending:
        # Get user email
        if submission.get('user_id'):
            user = get_user_service().get(submission['user_id'])
            submission['email'] = user.get('email', '') if user else ''

        # Get seller name
        if submission.get('seller_id'):
            seller = seller_service.get(submission['seller_id'])
            submission['seller_name'] = seller.get('name', '') if seller else ''

    return render_template('admin_verification.html', submissions=pending)


@admin_bp.route('/verification/<sub_id>/approve', methods=['POST'])
@admin_required
def approve_verification(sub_id):
    """Admin approves verification"""

    sub = verification_submission_service.get(sub_id)
    if not sub:
        return jsonify({'success': False, 'message': 'Submission not found'}), 404

    # Update verification status
    verification_submission_service.update_status(
        sub_id,
        'approved',
        reviewed_by=session.get('user', {}).get('id')
    )

    # Update user KYC status
    get_user_service().update(sub['user_id'], {'kyc_completed': True})

    # If seller verification, update seller and award badge
    if sub.get('seller_id'):
        seller_service.update(sub['seller_id'], {'verification_status': 'verified'})

        # Award first badge
        seller_badge_service.award_badge(
            sub['seller_id'],
            'Verified Merchant',
            'Verified seller on SparzaFI platform'
        )

    return jsonify({'success': True, 'message': 'Verification approved. User KYC and Seller badge issued.'})


@admin_bp.route('/moderation')
@admin_required
def admin_moderation():
    """Automated Content Moderation"""
    db = get_firestore_db()

    # Get pending moderation queue items
    queue_query = db.collection('moderation_queue').where(
        filter=FieldFilter('status', '==', 'pending')
    ).stream()

    queue = []
    for doc in queue_query:
        item = {**doc.to_dict(), 'id': doc.id}

        # Get seller name
        if item.get('seller_id'):
            seller = seller_service.get(item['seller_id'])
            item['seller_name'] = seller.get('name', '') if seller else ''

        # Get flagged by user email
        if item.get('flagged_by'):
            user = get_user_service().get(item['flagged_by'])
            item['flagged_by_email'] = user.get('email', '') if user else ''

        queue.append(item)

    return render_template('admin_moderation.html', queue=queue)


@admin_bp.route('/tax_compliance')
@admin_required
def admin_tax_compliance():
    """Tax and Compliance Section"""
    db = get_firestore_db()
    vat_rate = app.config['VAT_RATE']

    # Calculate VAT for the last month
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Query for all completed sales this month
    completed_trans = db.collection('transactions').where(
        filter=FieldFilter('status', '==', 'COMPLETED')
    ).stream()

    # Group by seller
    seller_vat = {}

    for doc in completed_trans:
        trans = doc.to_dict()

        # Check if transaction is from current month/year
        funds_settled_at = trans.get('funds_settled_at')
        if funds_settled_at and isinstance(funds_settled_at, str):
            try:
                settled_date = datetime.fromisoformat(funds_settled_at.replace('Z', '+00:00'))
                if settled_date.year == current_year and settled_date.month == current_month:
                    seller_id = trans.get('seller_id')
                    seller_amount = float(trans.get('seller_amount', 0))

                    if seller_id not in seller_vat:
                        seller_vat[seller_id] = {'gross_sales': 0.0, 'vat_due': 0.0}

                    seller_vat[seller_id]['gross_sales'] += seller_amount
                    seller_vat[seller_id]['vat_due'] += seller_amount * vat_rate
            except:
                pass

    # Enrich with seller names
    vat_reports = []
    for seller_id, data in seller_vat.items():
        seller = seller_service.get(seller_id)
        vat_reports.append({
            'seller_name': seller.get('name', '') if seller else 'Unknown',
            'total_gross_sales': data['gross_sales'],
            'vat_due': data['vat_due']
        })

    return render_template('admin_tax_compliance.html',
                         vat_reports=vat_reports,
                         vat_rate=vat_rate,
                         current_month=current_month,
                         current_year=current_year)


@admin_bp.route('/tax_compliance/export', methods=['POST'])
@admin_required
def export_vat_report():
    """Export VAT reports to CSV"""
    db = get_firestore_db()
    vat_rate = app.config['VAT_RATE']

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Seller Name', 'Total Gross Sales (R)', 'VAT Due (R)'])

    # Get current month data
    current_month = datetime.now().month
    current_year = datetime.now().year

    completed_trans = db.collection('transactions').where(
        filter=FieldFilter('status', '==', 'COMPLETED')
    ).stream()

    seller_vat = {}

    for doc in completed_trans:
        trans = doc.to_dict()
        funds_settled_at = trans.get('funds_settled_at')

        if funds_settled_at and isinstance(funds_settled_at, str):
            try:
                settled_date = datetime.fromisoformat(funds_settled_at.replace('Z', '+00:00'))
                if settled_date.year == current_year and settled_date.month == current_month:
                    seller_id = trans.get('seller_id')
                    seller_amount = float(trans.get('seller_amount', 0))

                    if seller_id not in seller_vat:
                        seller_vat[seller_id] = {'gross_sales': 0.0}

                    seller_vat[seller_id]['gross_sales'] += seller_amount
            except:
                pass

    # Write data rows
    for seller_id, data in seller_vat.items():
        seller = seller_service.get(seller_id)
        seller_name = seller.get('name', 'Unknown') if seller else 'Unknown'
        gross_sales = data['gross_sales']
        vat_due = gross_sales * vat_rate

        writer.writerow([seller_name, f"{gross_sales:.2f}", f"{vat_due:.2f}"])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=sparzafi_vat_report.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# ==================== VERIFICATION CODE MANAGEMENT ====================

@admin_bp.route('/api/cleanup-expired-codes', methods=['POST'])
@admin_required
def cleanup_expired_codes():
    """
    Admin endpoint to manually trigger cleanup of expired verification codes
    This should be run daily via cron job or scheduler
    """
    from deliverer.utils import expire_old_verification_codes

    result = expire_old_verification_codes()

    if result['success']:
        return jsonify({
            'success': True,
            'message': f"Successfully expired {result['expired_count']} old verification codes"
        }), 200
    else:
        return jsonify(result), 500
