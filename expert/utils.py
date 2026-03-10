from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Availability, TimeSlot, TimeOff, TherapistSettings
import logging

logger = logging.getLogger(__name__)

# ==================== EMAIL NOTIFICATION FUNCTIONS ====================

def send_booking_notification(booking, action='created'):
    """
    Send email notification about booking
    action: 'created', 'approved', 'rejected', 'cancelled', 'completed', 'reminder'
    """
    subject_map = {
        'created': 'New Session Request Received',
        'approved': 'Your Session Has Been Confirmed',
        'rejected': 'Session Request Update',
        'cancelled': 'Session Cancelled',
        'completed': 'Session Completed - Thank You',
        'reminder': 'Reminder: Upcoming Session Tomorrow',
    }
    
    template_map = {
        'created': 'emails/booking_created.html',
        'approved': 'emails/booking_approved.html',
        'rejected': 'emails/booking_rejected.html',
        'cancelled': 'emails/booking_cancelled.html',
        'completed': 'emails/booking_completed.html',
        'reminder': 'emails/booking_reminder.html',
    }
    
    subject = subject_map.get(action, 'Session Update')
    template = template_map.get(action, 'emails/booking_update.html')
    
    # Determine recipient based on action
    if action == 'created':
        # Send to expert
        recipient_email = booking.therapist.email
        recipient_name = booking.therapist.name
    else:
        # Send to user
        recipient_email = booking.user.email
        recipient_name = booking.user.get_full_name() or booking.user.username
    
    try:
        html_message = render_to_string(template, {
            'booking': booking,
            'user': booking.user,
            'therapist': booking.therapist,
            'action': action,
            'recipient_name': recipient_name,
        })
        plain_message = strip_tags(html_message)
        
        # Log instead of sending if email not configured
        if settings.DEFAULT_FROM_EMAIL:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                html_message=html_message,
                fail_silently=True,
            )
            logger.info(f"Email sent: {subject} to {recipient_email}")
        else:
            logger.info(f"[EMAIL SIMULATED] {subject} to {recipient_email}")
            logger.info(f"Booking: {booking.id} - {booking.booking_date} {booking.booking_time}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")


def send_session_reminder(booking):
    """Send reminder 1 hour before session"""
    send_booking_notification(booking, 'reminder')


# ==================== SLOT GENERATION FUNCTIONS ====================

def generate_time_slots(therapist, start_date=None, end_date=None):
    """
    Generate time slots from availability for a date range
    Returns: (slots_created, slots_updated) tuple
    """
    if not start_date:
        start_date = timezone.now().date()
    
    if not end_date:
        # Get therapist settings
        try:
            settings = TherapistSettings.objects.get(therapist=therapist)
            advance_days = settings.advance_booking_days
        except TherapistSettings.DoesNotExist:
            advance_days = 30
        
        end_date = start_date + timedelta(days=advance_days)
    
    # Get all active availability for the therapist
    availabilities = Availability.objects.filter(
        therapist=therapist,
        is_active=True
    )
    
    if not availabilities.exists():
        logger.warning(f"No availability found for therapist {therapist.id}")
        return 0, 0
    
    slots_created = 0
    slots_updated = 0
    
    # Generate slots for each day in range
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        
        # Get availability for this day of week
        day_availabilities = availabilities.filter(day_of_week=day_of_week)
        
        for availability in day_availabilities:
            created, updated = create_slots_from_availability(availability, current_date)
            slots_created += created
            slots_updated += updated
        
        current_date += timedelta(days=1)
    
    logger.info(f"Generated {slots_created} new slots, updated {slots_updated} existing slots for therapist {therapist.id}")
    return slots_created, slots_updated


def create_slots_from_availability(availability, date):
    """
    Create individual time slots from an availability for a specific date
    Returns: (created_count, updated_count) tuple
    """
    therapist = availability.therapist
    
    # Get settings
    try:
        settings = TherapistSettings.objects.get(therapist=therapist)
        session_duration = settings.session_duration
        buffer_time = settings.buffer_time
    except TherapistSettings.DoesNotExist:
        session_duration = 90
        buffer_time = 15
    
    # Convert times to datetime for calculation
    start_datetime = datetime.combine(date, availability.start_time)
    end_datetime = datetime.combine(date, availability.end_time)
    
    # Calculate total minutes available
    total_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
    
    # Calculate how many slots we can fit
    slot_plus_buffer = session_duration + buffer_time
    num_slots = total_minutes // slot_plus_buffer
    
    created_count = 0
    updated_count = 0
    
    # Check if this date is in time off period
    is_time_off = TimeOff.objects.filter(
        therapist=therapist,
        start_date__lte=date,
        end_date__gte=date,
        status='approved'
    ).exists()
    
    for i in range(num_slots):
        slot_start = start_datetime + timedelta(minutes=i * slot_plus_buffer)
        slot_end = slot_start + timedelta(minutes=session_duration)
        
        # Don't create slots that end after availability end
        if slot_end > end_datetime:
            continue
        
        # Check if slot already exists
        existing_slot = TimeSlot.objects.filter(
            therapist=therapist,
            date=date,
            start_time=slot_start.time()
        ).first()
        
        if existing_slot:
            # Update existing slot if needed
            if existing_slot.end_time != slot_end.time() or existing_slot.duration_minutes != session_duration:
                existing_slot.end_time = slot_end.time()
                existing_slot.duration_minutes = session_duration
                existing_slot.save()
                updated_count += 1
            continue
        
        # Create new slot
        TimeSlot.objects.create(
            therapist=therapist,
            availability=availability,
            date=date,
            start_time=slot_start.time(),
            end_time=slot_end.time(),
            duration_minutes=session_duration,
            is_available=not is_time_off,
            is_blocked=is_time_off
        )
        created_count += 1
    
    return created_count, updated_count


def generate_slots_for_date_range(therapist, start_date, end_date):
    """
    Generate slots for a specific date range
    Useful for admin operations
    """
    total_created = 0
    total_updated = 0
    
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()
        availabilities = Availability.objects.filter(
            therapist=therapist,
            day_of_week=day_of_week,
            is_active=True
        )
        
        for availability in availabilities:
            created, updated = create_slots_from_availability(availability, current_date)
            total_created += created
            total_updated += updated
        
        current_date += timedelta(days=1)
    
    return total_created, total_updated


# ==================== SLOT QUERY FUNCTIONS ====================

def get_available_slots(therapist, date=None):
    """
    Get all available slots for a therapist
    """
    queryset = TimeSlot.objects.filter(
        therapist=therapist,
        is_available=True,
        is_booked=False,
        is_blocked=False
    )
    
    if date:
        queryset = queryset.filter(date=date)
    else:
        queryset = queryset.filter(date__gte=timezone.now().date())
    
    return queryset.order_by('date', 'start_time')


def get_upcoming_slots(therapist, limit=10):
    """
    Get next available slots for a therapist
    """
    return TimeSlot.objects.filter(
        therapist=therapist,
        date__gte=timezone.now().date(),
        is_available=True,
        is_booked=False,
        is_blocked=False
    ).order_by('date', 'start_time')[:limit]


def check_slot_availability(therapist, date, time):
    """
    Check if a specific slot is available
    """
    return TimeSlot.objects.filter(
        therapist=therapist,
        date=date,
        start_time=time,
        is_available=True,
        is_booked=False,
        is_blocked=False
    ).exists()


# ==================== TIME OFF MANAGEMENT FUNCTIONS ====================

def block_slots_for_time_off(time_off):
    """
    Block all slots during a time off period
    Returns number of slots blocked
    """
    if time_off.status != 'approved':
        logger.warning(f"Time off {time_off.id} not approved, skipping slot blocking")
        return 0
    
    updated = TimeSlot.objects.filter(
        therapist=time_off.therapist,
        date__gte=time_off.start_date,
        date__lte=time_off.end_date,
        is_booked=False  # Don't block already booked slots
    ).update(
        is_available=False,
        is_blocked=True
    )
    
    logger.info(f"Blocked {updated} slots for time off {time_off.id}")
    return updated


def unblock_slots_for_time_off(time_off):
    """
    Unblock slots when time off is cancelled/rejected
    Returns number of slots unblocked
    """
    updated = TimeSlot.objects.filter(
        therapist=time_off.therapist,
        date__gte=time_off.start_date,
        date__lte=time_off.end_date,
        is_blocked=True
    ).update(
        is_available=True,
        is_blocked=False
    )
    
    logger.info(f"Unblocked {updated} slots for time off {time_off.id}")
    return updated


# ==================== CLEANUP FUNCTIONS ====================

def cleanup_past_slots(days=30):
    """
    Delete or archive slots older than specified days
    Returns number of slots cleaned up
    """
    cutoff_date = timezone.now().date() - timedelta(days=days)
    
    # Delete slots that are past and not booked
    deleted = TimeSlot.objects.filter(
        date__lt=cutoff_date,
        is_booked=False
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted} past slots")
    return deleted


def regenerate_missing_slots(therapist):
    """
    Check and regenerate any missing slots in the next 7 days
    Returns (created, updated) tuple
    """
    today = timezone.now().date()
    next_week = today + timedelta(days=7)
    
    created = 0
    updated = 0
    
    for date in (today + timedelta(days=i) for i in range(8)):
        day_of_week = date.weekday()
        availabilities = Availability.objects.filter(
            therapist=therapist,
            day_of_week=day_of_week,
            is_active=True
        )
        
        for availability in availabilities:
            # Check if slots exist for this day
            existing_slots = TimeSlot.objects.filter(
                therapist=therapist,
                date=date,
                availability=availability
            ).count()
            
            if existing_slots == 0:
                # Generate slots for this day
                c, u = create_slots_from_availability(availability, date)
                created += c
                updated += u
    
    return created, updated