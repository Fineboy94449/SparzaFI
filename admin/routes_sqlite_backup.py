from flask import render_template, redirect, url_for, session, request, abort, jsonify, make_response
from flask import current_app as app, g
from shared.utils import admin_required, get_db
from shared.components import render_chart_data
from . import admin_bp
import csv
from io import StringIO
from datetime import datetime

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard_enhanced():
    """15. Admin Analytics Dashboard"""
    db = get_db()

    # Get summary statistics
    total_sellers = db.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
    total_products = db.execute('SELECT COUNT(*) FROM products WHERE is_active = 1').fetchone()[0]
    total_transactions = db.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]

    # Calculate total revenue and commission
    revenue_data = db.execute('''
        SELECT
            COALESCE(SUM(total_amount), 0) as total_revenue,
            COALESCE(SUM(platform_commission), 0) as platform_commission
        FROM transactions
        WHERE status IN ('COMPLETED', 'DELIVERED')
    ''').fetchone()

    summary = {
        'total_sellers': total_sellers,
        'total_products': total_products,
        'total_transactions': total_transactions,
        'total_revenue': f"R{revenue_data['total_revenue']:.2f}",
        'platform_commission': f"R{revenue_data['platform_commission']:.2f}"
    }

    # Get recent transactions
    transactions = db.execute('''
        SELECT t.*, u.email as user_email, s.name as seller_name,
               'R' || PRINTF('%.2f', t.total_amount) as display_amount
        FROM transactions t
        LEFT JOIN users u ON t.user_id = u.id
        LEFT JOIN sellers s ON t.seller_id = s.id
        ORDER BY t.timestamp DESC
        LIMIT 15
    ''').fetchall()

    # Get all products
    products = db.execute('''
        SELECT p.name as product_name, p.description, p.price,
               s.name as seller_name, s.handle, s.verification_status,
               'R' || PRINTF('%.2f', p.price) as display_price
        FROM products p
        JOIN sellers s ON p.seller_id = s.id
        WHERE p.is_active = 1
        ORDER BY p.created_at DESC
    ''').fetchall()

    return render_template('admin_dashboard.html',
        summary=summary,
        transactions=[dict(t) for t in transactions],
        products=[dict(p) for p in products]
    )

@admin_bp.route('/verification')
@admin_required
def admin_verification():
    """1. Seller Verification Dashboard"""
    db = get_db()
    pending = db.execute("""
        SELECT vs.*, u.email, s.name as seller_name 
        FROM verification_submissions vs 
        JOIN users u ON vs.user_id = u.id 
        LEFT JOIN sellers s ON vs.seller_id = s.id
        WHERE vs.status = 'pending'
    """).fetchall()
    
    return render_template('admin_verification.html', submissions=[dict(p) for p in pending])

@admin_bp.route('/verification/<int:sub_id>/approve', methods=['POST'])
@admin_required
def approve_verification(sub_id):
    """1. Admin approves verification"""
    db = get_db()
    
    sub = db.execute('SELECT * FROM verification_submissions WHERE id = ?', (sub_id,)).fetchone()
    if not sub:
        return jsonify({'success': False, 'message': 'Submission not found'}), 404
        
    # Set verification status, add badge
    db.execute('UPDATE verification_submissions SET status = "approved", reviewed_at = CURRENT_TIMESTAMP WHERE id = ?', (sub_id,))
    db.execute('UPDATE users SET kyc_completed = 1 WHERE id = ?', (sub['user_id'],))
    
    if sub['seller_id']:
        db.execute('UPDATE sellers SET verification_status = "verified" WHERE id = ?', (sub['seller_id'],))
        # 14. NFT-style Seller Badges: Award first badge
        db.execute('INSERT OR IGNORE INTO seller_badges (seller_id, badge_name) VALUES (?, ?)', (sub['seller_id'], 'Verified Merchant'))
        
    db.commit()
    return jsonify({'success': True, 'message': 'Verification approved. User KYC and Seller badge issued.'})

@admin_bp.route('/moderation')
@admin_required
def admin_moderation():
    """16. Automated Content Moderation"""
    db = get_db()
    queue = db.execute("""
        SELECT mq.*, s.name as seller_name, u.email as flagged_by_email 
        FROM moderation_queue mq 
        JOIN sellers s ON mq.seller_id = s.id
        LEFT JOIN users u ON mq.flagged_by = u.id
        WHERE mq.status = 'pending'
    """).fetchall()
    
    return render_template('admin_moderation.html', queue=[dict(q) for q in queue])

@admin_bp.route('/tax_compliance')
@admin_required
def admin_tax_compliance():
    """17. Tax and Compliance Section"""
    db = get_db()
    vat_rate = app.config['VAT_RATE']
    
    # Calculate VAT for the last month (mock)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Query for all completed sales this month (for simplicity)
    vat_due_data = db.execute("""
        SELECT 
            s.name as seller_name, 
            SUM(t.seller_amount) as total_gross_sales, 
            SUM(t.seller_amount) * ? as vat_due
        FROM transactions t
        JOIN sellers s ON t.seller_id = s.id
        WHERE t.status = 'COMPLETED' 
        AND STRFTIME('%Y', t.funds_settled_at) = ?
        AND STRFTIME('%m', t.funds_settled_at) = ?
        GROUP BY s.name
    """, (vat_rate, str(current_year), f"{current_month:02}")).fetchall()
    
    vat_reports = [dict(v) for v in vat_due_data]

    return render_template('admin_tax_compliance.html', vat_reports=vat_reports, vat_rate=vat_rate, current_month=current_month, current_year=current_year)

@admin_bp.route('/tax_compliance/export', methods=['POST'])
@admin_required
def export_vat_report():
    """17. Export reports to CSV or PDF"""
    # Simplified CSV export
    output = StringIO()
    writer = csv.writer(output)
    
    # Example: Write header and mock data
    writer.writerow(['Seller Name', 'Total Gross Sales (R)', 'VAT Due (R)'])
    writer.writerow(['Thandi\'s Kitchen', '12500.00', '1875.00'])
    
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


# ... (Other admin routes: admin_users, admin_transactions, etc.)