import os
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'SparkZone <no-reply@sparkzone.in>')

def send_booking_confirmation_email(user, booking):
    """
    Sends responsive HTML booking receipt and pass to gamer.
    """
    subject = f"⚡ Booking Confirmed! Your SparkZone Pass #{booking.id}"
    units = booking.unit_numbers or str(booking.unit_number or 1)
    
    text_content = f"""
Hi {user.firstName},

Your gaming station booking at {booking.game.name} is confirmed!

Booking ID: SZ#{booking.id}
Date: {booking.bookingDate}
Time: {booking.startTime.strftime('%H:%M')} - {booking.endTime.strftime('%H:%M')}
Units: {units}
Venue: {booking.game.name}
Address: {booking.game.address}, {booking.game.city.name}
Amount: ₹{booking.totalAmount:.2f} ({booking.get_payment_status_display()})

Please arrive 10 minutes prior to your session start.
Team SparkZone
"""

    html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Booking Confirmed</title></head>
<body style="margin:0;padding:0;background-color:#080b11;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f0f4f8;">
  <div style="max-width:540px;margin:30px auto;background:#0f141d;border:1px solid #1e2638;border-radius:16px;overflow:hidden;padding:32px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
      <div style="width:36px;height:36px;border-radius:8px;background:#00f0ff;display:flex;align-items:center;justify-content:center;font-weight:900;color:#080b11;font-size:18px;">⚡</div>
      <span style="font-size:20px;font-weight:800;color:#f0f4f8;letter-spacing:-0.02em;">SparkZone</span>
    </div>
    
    <div style="display:inline-block;padding:4px 12px;border-radius:100px;background:rgba(0,240,255,0.12);color:#00f0ff;font-size:12px;font-weight:700;margin-bottom:12px;border:1px solid rgba(0,240,255,0.25);">
      BOOKING CONFIRMED (INSTANT LOCK)
    </div>
    
    <h2 style="font-size:22px;color:#ffffff;margin:0 0 8px 0;">Get Ready, {user.firstName}!</h2>
    <p style="color:#8896a8;font-size:14px;line-height:1.5;margin:0 0 24px 0;">Your gaming rig is locked and reserved for you.</p>
    
    <div style="background:#141b27;border:1px solid #1e293b;border-radius:12px;padding:20px;margin-bottom:24px;">
      <div style="display:flex;justify-content:space-between;padding-bottom:12px;border-bottom:1px solid #1e293b;font-size:13px;">
        <span style="color:#8896a8;">Station & Venue</span>
        <strong style="color:#f0f4f8;">{booking.game.name}</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1e293b;font-size:13px;">
        <span style="color:#8896a8;">Date & Slot</span>
        <strong style="color:#00f0ff;">{booking.bookingDate} ({booking.startTime.strftime('%H:%M')} - {booking.endTime.strftime('%H:%M')})</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #1e293b;font-size:13px;">
        <span style="color:#8896a8;">Unit / Console #</span>
        <strong style="color:#f0f4f8;">Unit(s) {units}</strong>
      </div>
      <div style="display:flex;justify-content:space-between;padding-top:12px;font-size:14px;">
        <span style="color:#8896a8;">Total Paid</span>
        <strong style="color:#10b981;">₹{booking.totalAmount:.2f} ({booking.get_payment_status_display()})</strong>
      </div>
    </div>
    
    <p style="color:#64748b;font-size:12px;line-height:1.5;margin:0;">Venue Address: {booking.game.address}, {booking.game.city.name}. Show this digital confirmation on arrival.</p>
  </div>
</body>
</html>
"""

    try:
        msg = EmailMultiAlternatives(subject, text_content, DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
        logger.info(f"Confirmation email sent to {user.email} for booking #{booking.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")
        return False

def send_cancellation_email(user, booking, refund_amount=0):
    """
    Sends booking cancellation and refund receipt email.
    """
    subject = f"Booking Cancelled - SparkZone Pass #{booking.id}"
    text_content = f"Hi {user.firstName}, your booking #{booking.id} at {booking.game.name} has been cancelled. Refund of ₹{refund_amount} initiated."
    
    try:
        msg = EmailMultiAlternatives(subject, text_content, DEFAULT_FROM_EMAIL, [user.email])
        msg.send(fail_silently=True)
        return True
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {e}")
        return False
