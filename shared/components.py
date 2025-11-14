from flask import session
import hashlib
import json

def get_cart_count(session):
    """Returns cart item count"""
    return sum(item['quantity'] for item in session.get('cart', {}).values())

def calculate_loyalty_points(total_amount, loyalty_rate):
    """20. Loyalty Program - Calculates points earned based on purchase total"""
    return round(total_amount * loyalty_rate, 2)

def generate_tx_hash(transaction_id, timestamp):
    """Generates a pseudo-blockchain transaction hash for explorer"""
    timestamp_hash = hashlib.sha1(str(timestamp).encode('utf-8')).hexdigest()[:8]
    return f"0x{transaction_id:06}{timestamp_hash}"

def render_chart_data(data, labels, title):
    """6. Seller Analytics Dashboard / 15. Admin Analytics Dashboard - Formats data for Chart.js"""
    return json.dumps({
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': title,
                'data': data,
                'backgroundColor': 'rgba(102, 126, 234, 0.5)',
                'borderColor': 'rgba(102, 126, 234, 1)',
                'borderWidth': 1
            }]
        }
    })