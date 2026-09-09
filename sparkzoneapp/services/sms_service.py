import os
import requests
import logging

logger = logging.getLogger(__name__)

MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY', '')
MSG91_SENDER_ID = os.getenv('MSG91_SENDER_ID', 'SPARKZ')
MSG91_FLOW_ID_CONFIRMATION = os.getenv('MSG91_FLOW_ID_CONFIRMATION', '')
MSG91_FLOW_ID_REMINDER = os.getenv('MSG91_FLOW_ID_REMINDER', '')
MSG91_FLOW_ID_CANCELLATION = os.getenv('MSG91_FLOW_ID_CANCELLATION', '')

def is_sms_configured():
    return bool(MSG91_AUTH_KEY)

def send_msg91_flow_sms(mobile, template_id, variables):
    """
    Sends a templated SMS using MSG91 Flow API.
    """
    if not MSG91_AUTH_KEY or not template_id:
        logger.info(f"[MSG91 MOCK SMS] To: {mobile} | Template: {template_id} | Data: {variables}")
        return {'success': True, 'mock': True}

    url = "https://control.msg91.com/api/v5/flow/"
    headers = {
        "authkey": MSG91_AUTH_KEY,
        "content-type": "application/json"
    }
    
    clean_mobile = str(mobile).strip()
    if not clean_mobile.startswith('91') and len(clean_mobile) == 10:
        clean_mobile = f"91{clean_mobile}"

    payload = {
        "template_id": template_id,
        "short_url": "1",
        "recipients": [
            {
                "mobiles": clean_mobile,
                **variables
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        res_data = response.json()
        logger.info(f"MSG91 SMS sent to {clean_mobile}: {res_data}")
        return {'success': True, 'response': res_data, 'mock': False}
    except Exception as e:
        logger.error(f"MSG91 SMS failed to {clean_mobile}: {e}")
        return {'success': False, 'error': str(e)}

def send_booking_confirmation_sms(phone, booking):
    """
    Sends instant booking confirmation SMS to Gamer.
    """
    units = booking.unit_numbers or str(booking.unit_number or 1)
    variables = {
        "NAME": booking.user.firstName,
        "STATION": booking.game.name,
        "DATE": str(booking.bookingDate),
        "TIME": f"{booking.startTime.strftime('%H:%M')}-{booking.endTime.strftime('%H:%M')}",
        "UNITS": units,
        "AMOUNT": str(int(booking.totalAmount)),
        "BOOKING_ID": f"SZ#{booking.id}"
    }
    return send_msg91_flow_sms(phone, MSG91_FLOW_ID_CONFIRMATION, variables)

def send_slot_reminder_sms(phone, booking):
    """
    Sends 1-hour session reminder SMS.
    """
    variables = {
        "NAME": booking.user.firstName,
        "STATION": booking.game.name,
        "TIME": booking.startTime.strftime('%H:%M'),
        "ADDRESS": booking.game.address
    }
    return send_msg91_flow_sms(phone, MSG91_FLOW_ID_REMINDER, variables)

def send_cancellation_sms(phone, booking, refund_amount=0):
    """
    Sends booking cancellation and refund status SMS.
    """
    variables = {
        "NAME": booking.user.firstName,
        "STATION": booking.game.name,
        "REFUND": str(int(refund_amount)),
        "BOOKING_ID": f"SZ#{booking.id}"
    }
    return send_msg91_flow_sms(phone, MSG91_FLOW_ID_CANCELLATION, variables)
