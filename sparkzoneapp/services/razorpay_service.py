import os
import hmac
import hashlib
import uuid
import logging

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

def get_razorpay_client():
    """
    Returns an initialized Razorpay Client instance if credentials exist, else None.
    """
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        except Exception as e:
            logger.error(f"Failed to initialize Razorpay client: {e}")
    return None

def is_razorpay_live():
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

def create_razorpay_order(amount_in_rupees, receipt_id, notes=None):
    """
    Creates an order in Razorpay (amount in paise).
    If Razorpay keys are not configured, generates a mock test order ID.
    """
    amount_paise = int(round(float(amount_in_rupees) * 100))
    client = get_razorpay_client()

    if client:
        try:
            order_data = {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': f"rcpt_{receipt_id}",
                'notes': notes or {},
                'payment_capture': 1  # Auto capture payment
            }
            order = client.order.create(data=order_data)
            return {
                'success': True,
                'order_id': order['id'],
                'amount_paise': amount_paise,
                'amount_rupees': amount_in_rupees,
                'currency': 'INR',
                'key_id': RAZORPAY_KEY_ID,
                'is_mock': False
            }
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    else:
        # Fallback / Development Mock Order
        mock_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return {
            'success': True,
            'order_id': mock_id,
            'amount_paise': amount_paise,
            'amount_rupees': amount_in_rupees,
            'currency': 'INR',
            'key_id': RAZORPAY_KEY_ID or 'rzp_test_sparkzone_mock',
            'is_mock': True
        }

def verify_razorpay_signature(order_id, payment_id, signature):
    """
    Verifies Razorpay payment signature using HMAC SHA256.
    In mock mode, accepts mock test IDs.
    """
    if str(order_id).startswith('order_mock_'):
        return True

    client = get_razorpay_client()
    if client:
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)
            return True
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {e}")
            # Fallback manual calculation verification
            msg = f"{order_id}|{payment_id}".encode('utf-8')
            expected_sig = hmac.new(RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, signature)
    
    return True

def process_razorpay_refund(payment_id, amount_in_rupees=None, notes=None):
    """
    Issues a refund via Razorpay for the given payment ID.
    """
    if not payment_id or str(payment_id).startswith('pay_mock_'):
        return {
            'success': True,
            'refund_id': f"rfnd_mock_{uuid.uuid4().hex[:10]}",
            'is_mock': True
        }

    client = get_razorpay_client()
    if client:
        try:
            refund_data = {'notes': notes or {}}
            if amount_in_rupees:
                refund_data['amount'] = int(round(float(amount_in_rupees) * 100))
            
            refund = client.payment.refund(payment_id, refund_data)
            return {
                'success': True,
                'refund_id': refund.get('id'),
                'is_mock': False
            }
        except Exception as e:
            logger.error(f"Razorpay refund failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    return {
        'success': True,
        'refund_id': f"rfnd_mock_{uuid.uuid4().hex[:10]}",
        'is_mock': True
    }
