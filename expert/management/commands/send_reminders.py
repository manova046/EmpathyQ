from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from user.models import SessionBooking
from expert.utils import send_session_reminder

class Command(BaseCommand):
    help = 'Send session reminders for upcoming sessions'

    def handle(self, *args, **options):
        now = timezone.now()
        reminder_time = now + timedelta(hours=1)
        
        # Get sessions starting in approximately 1 hour
        upcoming_sessions = SessionBooking.objects.filter(
            booking_date=now.date(),
            booking_time__hour=reminder_time.hour,
            booking_time__minute=reminder_time.minute,
            status='confirmed'
        )
        
        for session in upcoming_sessions:
            send_session_reminder(session)
            self.stdout.write(f'Reminder sent for session {session.id}')