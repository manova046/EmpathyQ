# user/models.py - COMPLETE UPDATED VERSION WITH ALL FIELDS
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import json
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class EmotionalQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=[
        ('energy', 'Energy Level'),
        ('mood', 'Core Mood'),
        ('stress', 'Stress/Anxiety'),
        ('focus', 'Focus/Motivation'),
        ('social', 'Social Connection'),
    ], default='mood')
    weight = models.FloatField(default=1.0, validators=[MinValueValidator(0.1), MaxValueValidator(3.0)])
    
    def __str__(self):
        return f"{self.question_text} ({self.category})"

# In user/models.py - Update MOOD_CHOICES

class EmotionalOption(models.Model):
    MOOD_CHOICES = [
        ('low', 'Low/Depressed/Sad'),
        ('stressed', 'Stressed/Overwhelmed'),
        ('calm', 'Calm/Relaxed/Peaceful'),
        ('motivated', 'Motivated/Energetic/Productive'),
        ('anxious', 'Anxious/Worried/Nervous'),
        ('neutral', 'Neutral/Balanced/Okay'),
        ('irritable', 'Irritable/Frustrated/Annoyed'),
        ('happy', 'Happy/Joyful/Content'),  # NEW
        ('excited', 'Excited/Enthusiastic/Thrilled'),  # NEW
        ('grateful', 'Grateful/Appreciative/Thankful'),  # NEW
        ('hopeful', 'Hopeful/Optimistic/Positive'),  # NEW
        ('lonely', 'Lonely/Isolated/Abandoned'),  # NEW
        ('overwhelmed', 'Overwhelmed/Unable to cope'),  # NEW
        ('peaceful', 'Peaceful/Serene/Tranquil'),  # NEW
        ('energetic', 'Energetic/Lively/Vibrant'),  # NEW
        ('tired', 'Tired/Exhausted/Drained'),  # NEW
        ('confused', 'Confused/Uncertain/Lost'),  # NEW
        ('hopeless', 'Hopeless/Despair/Discouraged'),  # NEW
        ('loved', 'Loved/Cared for/Appreciated'),  # NEW
        ('proud', 'Proud/Accomplished/Confident'),  # NEW
    ]
    
    # ... rest of the model remains the same
    question = models.ForeignKey(EmotionalQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=200)
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    intensity_score = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Intensity of this emotion (1-10)"
    )
    
    def __str__(self):
        return f"{self.option_text} ({self.mood}, intensity: {self.intensity_score})"

class EmotionalCheckIn(models.Model):
    MOOD_CHOICES = EmotionalOption.MOOD_CHOICES
    
    ENERGY_LEVELS = [
        ('low', 'Low Energy'),
        ('medium', 'Medium Energy'),
        ('high', 'High Energy'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emotional_checkins')
    created_at = models.DateTimeField(auto_now_add=True)
    primary_mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    secondary_mood = models.CharField(max_length=20, choices=MOOD_CHOICES, null=True, blank=True)
    intensity_score = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Energy level field
    energy_level = models.CharField(
        max_length=20,
        choices=ENERGY_LEVELS,
        default='medium',
        null=True,
        blank=True,
        help_text="Energy level derived from mood analysis"
    )
    
    # Mood profile field (JSON field to store patterns)
    mood_profile = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        help_text="Stores mood analysis patterns and profiles"
    )
    
    notes = models.TextField(blank=True, null=True, help_text="Optional personal notes about how you're feeling")
    
    # Legacy field for backward compatibility
    final_mood = models.CharField(
        max_length=20, 
        choices=MOOD_CHOICES, 
        null=True, 
        blank=True,
        help_text="Legacy field - use primary_mood for new code"
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Auto-populate final_mood from primary_mood if not set
        if not self.final_mood and self.primary_mood:
            self.final_mood = self.primary_mood
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user} - {self.primary_mood} ({self.intensity_score}/10) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class EmotionalAnswer(models.Model):
    checkin = models.ForeignKey(EmotionalCheckIn, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(EmotionalQuestion, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(EmotionalOption, on_delete=models.CASCADE)
    
    # created_at timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['checkin', 'question']
    
    def __str__(self):
        return f"{self.question} → {self.selected_option.mood}"

# ===== FIXED TASK CATEGORY MODEL =====
class TaskCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)  # ADDED: description field for fixtures
    icon = models.CharField(max_length=10, default='🌱')
    
    def __str__(self):
        return self.name

class AtomicTask(models.Model):
    MOOD_CHOICES = EmotionalOption.MOOD_CHOICES
    ENERGY_LEVELS = EmotionalCheckIn.ENERGY_LEVELS
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    energy_level = models.CharField(max_length=20, choices=ENERGY_LEVELS, default='medium')
    duration_minutes = models.IntegerField(default=5)
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='atomic_tasks')
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Make these optional with null=True, blank=True
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} ({self.mood}, {self.energy_level})"

class UserTaskAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_assignments')
    task = models.ForeignKey(AtomicTask, on_delete=models.CASCADE, related_name='assignments')
    checkin = models.ForeignKey(EmotionalCheckIn, on_delete=models.CASCADE, related_name='task_assignments', null=True, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # is_completed field
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['user', 'task', 'checkin']  # Prevent duplicate assignments
    
    def __str__(self):
        return f"{self.user} - {self.task.title} ({'completed' if self.is_completed else 'pending'})"

# Original EmotionalTask model for backward compatibility
class EmotionalTask(models.Model):
    """Original EmotionalTask model for backward compatibility"""
    MOOD_CHOICES = [
        ('low', 'Low'),
        ('stressed', 'Stressed'),
        ('calm', 'Calm'),
        ('motivated', 'Motivated'),
        ('anxious', 'Anxious'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    duration_minutes = models.IntegerField(default=15)
    
    def __str__(self):
        return f"{self.title} ({self.mood})"

# ===== NEW MODELS FOR ADDED FEATURES =====

class SessionCategory(models.Model):
    """Categories for therapy sessions"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, default='fas fa-video')
    
    def __str__(self):
        return self.name

class Therapist(models.Model):
    """Therapist/Counselor model"""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    specialization = models.CharField(max_length=200)
    bio = models.TextField()
    profile_image = models.ImageField(upload_to='therapists/', blank=True, null=True)
    categories = models.ManyToManyField(SessionCategory, related_name='therapists')
    is_available = models.BooleanField(default=True)
    rating = models.FloatField(default=0.0)
    total_sessions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Dr. {self.name} - {self.specialization}"

class SessionBooking(models.Model):
    """User's therapy session bookings"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),  # ADD THIS LINE
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('free', 'Free Session'),
    ]
    
    MEETING_PLATFORM_CHOICES = [
        ('google_meet', 'Google Meet'),
        ('jitsi', 'Jitsi Meet'),
        ('zoom', 'Zoom'),
        ('custom', 'Custom Link'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booked_sessions')
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, related_name='sessions')
    category = models.ForeignKey(SessionCategory, on_delete=models.CASCADE)
    
    # Booking Details
    booking_date = models.DateField()
    booking_time = models.TimeField()
    duration_minutes = models.IntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Meeting Details
    meeting_link = models.URLField(blank=True, null=True)
    meeting_platform = models.CharField(max_length=20, choices=MEETING_PLATFORM_CHOICES, default='jitsi')
    meeting_id = models.CharField(max_length=100, blank=True, null=True)
    meeting_password = models.CharField(max_length=50, blank=True, null=True)
    
    # Payment Details
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Cancellation Details
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.CharField(max_length=20, choices=[
        ('user', 'User'),
        ('expert', 'Expert'),
        ('admin', 'Admin'),
        ('system', 'System'),
    ], null=True, blank=True)
    
    # Reschedule Tracking
    original_booking_id = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='rescheduled_sessions')
    reschedule_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-booking_date', '-booking_time']
        unique_together = ['therapist', 'booking_date', 'booking_time']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['therapist', 'status']),
            models.Index(fields=['booking_date', 'status']),
            models.Index(fields=['meeting_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Dr. {self.therapist.name} - {self.booking_date} {self.booking_time}"
    
    def generate_meeting_link(self):
        """Generate a meeting link based on the selected platform"""
        import uuid
        import hashlib
        from datetime import datetime
        
        # Create a unique meeting ID using booking details
        unique_string = f"empathyq-{self.id}-{self.user.id}-{self.therapist.id}-{self.booking_date}-{self.booking_time}"
        self.meeting_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
        if self.meeting_platform == 'google_meet':
            # For Google Meet (requires Google Workspace)
            # Format: https://meet.google.com/xxx-xxxx-xxx
            self.meeting_link = f"https://meet.google.com/{self.meeting_id[:3]}-{self.meeting_id[3:7]}-{self.meeting_id[7:]}"
            
        elif self.meeting_platform == 'jitsi':
            # Jitsi Meet - Free and open source
            room_name = f"EmpathyQ-{self.id}-{self.meeting_id}"
            self.meeting_link = f"https://meet.jit.si/{room_name}"
            
        elif self.meeting_platform == 'zoom':
            # For Zoom (requires Zoom API integration)
            # This is a placeholder - implement actual Zoom API call
            self.meeting_link = f"https://zoom.us/j/{self.meeting_id}"
            self.meeting_password = str(uuid.uuid4())[:8]
            
        else:
            # Custom link - leave as is or generate a default
            if not self.meeting_link:
                self.meeting_link = f"https://meet.jit.si/EmpathyQ-{self.id}-{self.meeting_id}"
        
        self.save(update_fields=['meeting_link', 'meeting_id', 'meeting_password'])
        return self.meeting_link
    
    def save(self, *args, **kwargs):
        """Override save to handle meeting link generation and timestamps"""
        # Generate meeting link when status changes to confirmed or paid
        if self.status in ['confirmed', 'paid'] and not self.meeting_link:
            self.generate_meeting_link()
            if self.status == 'confirmed' and not self.confirmed_at:
                self.confirmed_at = timezone.now()
        
        # Set completed_at when status changes to completed
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        # Set cancelled_at when status changes to cancelled
        elif self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_upcoming(self):
        """Check if session is upcoming"""
        from django.utils import timezone
        from datetime import datetime
        
        session_datetime = datetime.combine(self.booking_date, self.booking_time)
        session_datetime = timezone.make_aware(session_datetime)
        return session_datetime > timezone.now() and self.status in ['confirmed', 'paid']
    
    @property
    def can_join(self):
        """Check if user can join the session now"""
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        # Allow joining for confirmed OR paid sessions
        if self.status not in ['confirmed', 'paid']:
            return False
        
        session_datetime = datetime.combine(self.booking_date, self.booking_time)
        session_datetime = timezone.make_aware(session_datetime)
        now = timezone.now()
        
        # Can join 15 minutes before and up to 30 minutes after
        early_join = session_datetime - timedelta(minutes=15)
        late_join = session_datetime + timedelta(minutes=30)
        
        return early_join <= now <= late_join
    
    @property
    def time_until_session(self):
        """Get time until session starts"""
        from django.utils import timezone
        from datetime import datetime
        
        # Allow for confirmed OR paid sessions
        if self.status not in ['confirmed', 'paid']:
            return None
        
        session_datetime = datetime.combine(self.booking_date, self.booking_time)
        session_datetime = timezone.make_aware(session_datetime)
        now = timezone.now()
        
        if session_datetime > now:
            delta = session_datetime - now
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if delta.days > 0:
                return f"{delta.days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "Session time passed"
    
    def cancel_booking(self, cancelled_by='user', reason=''):
        """Cancel the booking and release the time slot"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save()
        
        # Release the time slot if it exists
        try:
            from expert.models import TimeSlot
            time_slot = TimeSlot.objects.get(
                therapist=self.therapist,
                date=self.booking_date,
                start_time=self.booking_time,
                is_booked=True
            )
            time_slot.release()
        except TimeSlot.DoesNotExist:
            pass
        
        return True
    
    def complete_session(self):
        """Mark session as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        
        # Update therapist statistics
        try:
            from expert.models import TherapistSettings
            settings, created = TherapistSettings.objects.get_or_create(therapist=self.therapist)
            settings.total_sessions += 1
            if self.consultation_fee:
                settings.total_earnings += self.consultation_fee
            settings.save()
        except:
            pass
        
        return True
    
    def reschedule_session(self, new_date, new_time):
        """Reschedule the session to a new date/time"""
        # Check if new slot is available
        from expert.models import TimeSlot
        new_slot = TimeSlot.objects.filter(
            therapist=self.therapist,
            date=new_date,
            start_time=new_time,
            is_available=True,
            is_booked=False
        ).first()
        
        if not new_slot:
            return False, "Selected time slot is not available"
        
        # Store original booking reference
        original_id = self.id
        
        # Release old slot
        old_slot = TimeSlot.objects.get(
            therapist=self.therapist,
            date=self.booking_date,
            start_time=self.booking_time
        )
        old_slot.release()
        
        # Update booking
        self.booking_date = new_date
        self.booking_time = new_time
        self.status = 'confirmed'  # Keep confirmed status
        self.reschedule_count += 1
        self.save()
        
        # Book new slot
        new_slot.book(self)
        
        # Regenerate meeting link if needed
        if self.meeting_link:
            self.generate_meeting_link()
        
        return True, "Session rescheduled successfully"
    
    def get_meeting_details(self):
        """Get formatted meeting details for display"""
        if not self.meeting_link:
            return None
        
        platform_icons = {
            'google_meet': 'fab fa-google',
            'jitsi': 'fas fa-video',
            'zoom': 'fas fa-video',
            'custom': 'fas fa-link',
        }
        
        return {
            'link': self.meeting_link,
            'platform': self.get_meeting_platform_display(),
            'icon': platform_icons.get(self.meeting_platform, 'fas fa-video'),
            'id': self.meeting_id,
            'password': self.meeting_password,
            'can_join': self.can_join,
        }
    
    def send_notification(self, notification_type):
        """Send notification about booking status change"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        templates = {
            'confirmed': 'emails/session_confirmed.html',
            'cancelled': 'emails/session_cancelled.html',
            'reminder': 'emails/session_reminder.html',
            'completed': 'emails/session_completed.html',
            'paid': 'emails/payment_confirmation.html',  # ADD THIS
        }
        
        subjects = {
            'confirmed': f'✅ Session Confirmed with Dr. {self.therapist.name}',
            'cancelled': f'❌ Session Cancelled - {self.booking_date}',
            'reminder': f'⏰ Reminder: Your Session with Dr. {self.therapist.name}',
            'completed': f'✨ Session Completed - Share Your Feedback',
            'paid': f'💰 Payment Confirmed for Session with Dr. {self.therapist.name}',  # ADD THIS
        }
        
        if notification_type in templates:
            context = {
                'booking': self,
                'user': self.user,
                'therapist': self.therapist,
                'meeting_link': self.meeting_link,
            }
            
            html_message = render_to_string(templates[notification_type], context)
            
            send_mail(
                subjects[notification_type],
                '',  # Plain text version
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                html_message=html_message,
                fail_silently=True,
            )
    
  # In user/models.py - Fix the confirm_booking method (around line 600)
def confirm_booking(self):
    """Confirm booking after expert approval - sets fee from therapist settings"""
    self.status = 'confirmed'
    self.confirmed_at = timezone.now()
    
    # Get therapist's fee from settings
    from expert.models import TherapistSettings, ExpertProfileSettings
    
    fee = Decimal('500.00')  # Default
    
    # ===== FIXED: Prioritize ExpertProfileSettings =====
    try:
        # Try ExpertProfileSettings FIRST
        profile_settings = ExpertProfileSettings.objects.get(therapist=self.therapist)
        if profile_settings.consultation_fee:
            fee = profile_settings.consultation_fee
            print(f"Confirm booking using fee from ExpertProfileSettings: {fee}")
    except ExpertProfileSettings.DoesNotExist:
        try:
            # Try TherapistSettings SECOND
            therapist_settings = TherapistSettings.objects.get(therapist=self.therapist)
            if therapist_settings.consultation_fee:
                fee = therapist_settings.consultation_fee
                print(f"Confirm booking using fee from TherapistSettings: {fee}")
        except TherapistSettings.DoesNotExist:
            # Try therapist model's session_fee if exists
            if hasattr(self.therapist, 'session_fee') and self.therapist.session_fee:
                fee = self.therapist.session_fee
                print(f"Confirm booking using fee from therapist.session_fee: {fee}")
    
    # FIXED: Remove total_amount, only set consultation_fee
    self.consultation_fee = fee
    self.save()
    print(f"Booking {self.id} confirmed with fee: {fee}")
    
    return self

class ProgressTracker(models.Model):
    """Track user's progress over time"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_trackers')
    date = models.DateField(auto_now_add=True)
    mood_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True
    )
    anxiety_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True
    )
    sleep_hours = models.FloatField(null=True, blank=True)
    exercise_minutes = models.IntegerField(null=True, blank=True)
    tasks_completed = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']  # One entry per user per day
    
    def __str__(self):
        return f"{self.user} - {self.date}"
    




# user/models.py - CHAT SESSION MODELS ONLY
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

User = settings.AUTH_USER_MODEL

# =========================================
# Anonymous Chat Room
# =========================================

class AnonymousChatRoom(models.Model):
    ROOM_STATUS = (
        ('searching', 'Searching'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled'),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_user1'
    )

    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_user2',
        null=True,
        blank=True
    )

    mood_user1 = models.CharField(max_length=50)
    mood_user2 = models.CharField(max_length=50, null=True, blank=True)

    alias_user1 = models.CharField(max_length=50)
    alias_user2 = models.CharField(max_length=50, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=ROOM_STATUS,
        default='searching'
    )

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    duration_minutes = models.PositiveIntegerField(default=5)
    
    # Fields for better tracking
    last_activity = models.DateTimeField(auto_now=True)
    ended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ended_chat_rooms'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def start_chat(self):
        self.status = 'active'
        self.started_at = timezone.now()
        self.save()

    def end_chat(self, ended_by=None):
        self.status = 'ended'
        self.ended_at = timezone.now()
        if ended_by:
            self.ended_by = ended_by
        self.save()

    def is_expired(self):
        if self.started_at:
            expiry_time = self.started_at + timezone.timedelta(minutes=self.duration_minutes)
            return timezone.now() >= expiry_time
        return False
    
    def get_other_user(self, user):
        """Get the other user in the chat"""
        if user == self.user1:
            return self.user2
        return self.user1
    
    def get_user_alias(self, user):
        """Get alias for a specific user"""
        if user == self.user1:
            return self.alias_user1
        return self.alias_user2
    
    def get_other_alias(self, user):
        """Get alias for the other user"""
        if user == self.user1:
            return self.alias_user2
        return self.alias_user1
    
    def get_user_mood(self, user):
        """Get mood for a specific user"""
        if user == self.user1:
            return self.mood_user1
        return self.mood_user2

    def __str__(self):
        return f"Room {self.id} - {self.status}"


# =========================================
# Chat Messages
# =========================================

class ChatMessage(models.Model):
    room = models.ForeignKey(
        AnonymousChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    message = models.TextField()

    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.CharField(max_length=255, null=True, blank=True)
    
    # Fields for better message tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
        ]

    def __str__(self):
        return f"Message in {self.room.id}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


# =========================================
# Chat Feedback
# =========================================

class ChatFeedback(models.Model):
    FEELING_CHOICES = [
        ('much_better', 'Much better'),
        ('better', 'Better than before'),
        ('same', 'About the same'),
        ('worse', 'Still struggling'),
    ]
    
    HELPFUL_CHOICES = [
        ('yes', 'Yes, very helpful'),
        ('somewhat', 'Somewhat helpful'),
        ('no', 'No, not helpful'),
    ]
    
    room = models.ForeignKey(
        AnonymousChatRoom, 
        on_delete=models.CASCADE, 
        related_name='feedbacks'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    
    feeling_after = models.CharField(
        max_length=20, 
        choices=FEELING_CHOICES
    )
    
    was_helpful = models.CharField(
        max_length=10,
        choices=HELPFUL_CHOICES,
        default='yes'
    )
    
    comments = models.TextField(blank=True)
    
    # Additional feedback fields
    would_recommend = models.BooleanField(default=True)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        null=True,
        blank=True,
        help_text="Rating from 1-5"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['room', 'user']  # Prevent duplicate feedback
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Feedback from {self.user.username} for room {self.room.id}"


# =========================================
# Chat Matching Queue
# =========================================

# user/models.py - Update ChatQueue model

class ChatQueue(models.Model):
    ENERGY_LEVELS = [
        ('low', 'Low Energy'),
        ('medium', 'Medium Energy'),
        ('high', 'High Energy'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    
    mood = models.CharField(max_length=50)
    secondary_mood = models.CharField(max_length=50, null=True, blank=True)
    intensity = models.IntegerField(default=5)  # 1-10 scale
    energy_level = models.CharField(
        max_length=10,
        choices=ENERGY_LEVELS,
        default='medium'
    )
    mood_profile = models.JSONField(default=dict, blank=True)  # Store full profile
    
    # Queue management fields
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Set expiry time to 5 minutes from join time
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if queue entry has expired"""
        if self.expires_at:
            return timezone.now() >= self.expires_at
        return False

    def get_wait_time(self):
        """Get wait time in seconds"""
        if self.joined_at:
            return int((timezone.now() - self.joined_at).total_seconds())
        return 0

    def __str__(self):
        return f"{self.user} waiting in queue"
# =========================================
# Chat Reports (for flagged messages)
# =========================================

class ChatReport(models.Model):
    """
    Model for reporting inappropriate messages or behavior in chat
    """
    REPORT_REASONS = [
        ('harassment', 'Harassment'),
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate content'),
        ('other', 'Other'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'Pending Review'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    room = models.ForeignKey(
        AnonymousChatRoom,
        on_delete=models.CASCADE,
        related_name='reports'
    )
    
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_reports_made'
    )
    
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_reports_received',
        null=True,
        blank=True
    )
    
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField(blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=REPORT_STATUS,
        default='pending'
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_reports_reviewed'
    )
    
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report #{self.id} - {self.reason}"
    
    def review(self, reviewed_by, status, notes=''):
        self.status = status
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.resolution_notes = notes
        self.save()



from django.db import models
from django.conf import settings

class GameScore(models.Model):
    GAME_CHOICES = [
        ('RPS', 'Rock Paper Scissors'),
        ('SUDOKU', 'Sudoku'),
        ('MEMORY', 'Memory Match'),
        ('BREATHING', 'Color Breathing'),
        ('BUBBLEPOP', 'Bubble Pop'),
        ('COLORING', 'Mindful Coloring'),
        ('ODDEVEN', 'Odd or Even'),  # New game
        ('SOS', 'SOS Game'),          # New game
        ('SNAKE', 'Snake Eating Balls'),
    ]
    
    # Rest of the model remains exactly the same
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_scores')
    game = models.CharField(max_length=10, choices=GAME_CHOICES)
    highest_score = models.IntegerField(default=0)
    best_time = models.IntegerField(null=True, blank=True)
    games_played = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    last_played = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'game']
        
    def __str__(self):
        return f"{self.user.username} - {self.get_game_display()}: {self.highest_score}"






# Add this model to your existing models.py

# Add this model to your existing models.py

class Review(models.Model):
    """User reviews for therapists"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    therapist = models.ForeignKey(Therapist, on_delete=models.CASCADE, related_name='reviews_received')
    session = models.ForeignKey(
        'SessionBooking', 
        on_delete=models.CASCADE, 
        related_name='user_review',  # CHANGED: from 'review' to 'user_review'
        null=True, 
        blank=True
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating from 1 to 5 stars")
    comment = models.TextField()
    is_anonymous = models.BooleanField(default=False, help_text="Post review anonymously")
    is_approved = models.BooleanField(default=True, help_text="Admin approval for review")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'therapist', 'session']  # One review per session
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.therapist.name} - {self.rating}★"
    
    def save(self, *args, **kwargs):
        # Update therapist's average rating when review is saved
        super().save(*args, **kwargs)
        self.update_therapist_rating()
    
    def update_therapist_rating(self):
        """Update therapist's average rating"""
        from django.db.models import Avg
        avg_rating = Review.objects.filter(
            therapist=self.therapist, 
            is_approved=True
        ).aggregate(Avg('rating'))['rating__avg']
        
        if avg_rating:
            self.therapist.rating = round(avg_rating, 1)
            self.therapist.save()





class Payment(models.Model):
    """Payment model for tracking Razorpay payments"""
    PAYMENT_STATUS = [
        ('created', 'Created'),
        ('attempted', 'Attempted'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    booking = models.OneToOneField(
        'SessionBooking',
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='created')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Payments"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status}"
    
    def mark_as_paid(self, payment_id, signature):
        """Mark payment as paid"""
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save()
        
        # Update booking payment status and set to paid status
        self.booking.payment_status = 'paid'
        self.booking.status = 'paid'  # Change from 'confirmed' to 'paid'
        self.booking.save()