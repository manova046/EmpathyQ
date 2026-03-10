# user/utils.py
from django.utils import timezone
from datetime import timedelta
from .models import SessionBooking

def send_session_reminders():
    """Send reminders for sessions happening in 1 hour"""
    reminder_time = timezone.now() + timedelta(hours=1)
    
    upcoming_sessions = SessionBooking.objects.filter(
        status='confirmed',
        booking_date=reminder_time.date(),
        booking_time__hour=reminder_time.hour,
        booking_time__minute=reminder_time.minute,
    )
    
    for session in upcoming_sessions:
        session.send_notification('reminder')
    
    return upcoming_sessions.count()

def cleanup_expired_sessions():
    """Mark no-show for sessions that passed without being completed"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    expired_sessions = SessionBooking.objects.filter(
        status='confirmed',
        booking_date__lte=yesterday
    )
    
    for session in expired_sessions:
        session.status = 'no_show'
        session.save()
    
    return expired_sessions.count()