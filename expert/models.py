from django.db import models
from django.conf import settings
from django.utils import timezone
from user.models import Therapist
from datetime import timedelta
from django.db.models import Sum, Avg
from django.db.models.signals import post_save
from django.dispatch import receiver

class ExpertProfileSettings(models.Model):
    """Expert profile settings and preferences"""
    therapist = models.OneToOneField(
        Therapist,
        on_delete=models.CASCADE,
        related_name='profile_settings'
    )
    # Profile Media
    profile_photo = models.ImageField(upload_to='expert/profile_photos/%Y/%m/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='expert/cover_photos/%Y/%m/', null=True, blank=True)
    
    # Professional Information
    professional_title = models.CharField(max_length=200, blank=True, help_text="e.g., Clinical Psychologist, Licensed Therapist")
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    session_duration = models.IntegerField(default=60, help_text="Session duration in minutes")
    
    # Services
    video_enabled = models.BooleanField(default=True)
    chat_enabled = models.BooleanField(default=True)
    phone_enabled = models.BooleanField(default=False)
    
    # Booking Settings
    instant_booking = models.BooleanField(default=False)
    advance_booking_days = models.IntegerField(default=30)
    cancellation_policy = models.TextField(default="24 hours notice required for cancellation")
    
    # Profile Information
    about_me = models.TextField(blank=True)
    languages = models.CharField(max_length=500, blank=True, help_text="Comma separated languages (e.g., English, Spanish, French)")
    qualifications = models.TextField(blank=True, help_text="Enter each qualification on a new line")
    experience_years = models.IntegerField(default=0)
    
    # Specializations and Expertise (stored as comma-separated values)
    specializations = models.TextField(blank=True, help_text="Comma separated specializations")
    expertise_areas = models.TextField(blank=True, help_text="Comma separated areas of expertise")
    
    # Phone Numbers (stored as JSON)
    phone_numbers = models.JSONField(default=list, blank=True, help_text="List of phone numbers with type")
    
    # Privacy Settings
    is_profile_public = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Expert Profile Settings"
    
    def __str__(self):
        return f"Settings for {self.therapist.name}"
    
    def get_languages_list(self):
        """Return languages as a list"""
        if self.languages:
            return [lang.strip() for lang in self.languages.split(',') if lang.strip()]
        return []
    
    def get_specializations_list(self):
        """Return specializations as a list"""
        if self.specializations:
            return [spec.strip() for spec in self.specializations.split(',') if spec.strip()]
        return []
    
    def get_expertise_list(self):
        """Return expertise areas as a list"""
        if self.expertise_areas:
            return [exp.strip() for exp in self.expertise_areas.split(',') if exp.strip()]
        return []
    
    def get_qualifications_list(self):
        """Return qualifications as a list"""
        if self.qualifications:
            return [qual.strip() for qual in self.qualifications.split('\n') if qual.strip()]
        return []


class Review(models.Model):
    """Expert reviews from users"""
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_reviews'
    )
    booking = models.OneToOneField(
        'user.SessionBooking',
        on_delete=models.CASCADE,
        related_name='review'
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['therapist', 'user', 'booking']
    
    def __str__(self):
        return f"{self.user.username} - {self.therapist.name} - {self.rating}★"


class Availability(models.Model):
    """Expert availability schedule - Define working hours"""
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    therapist = models.ForeignKey(
        Therapist, 
        on_delete=models.CASCADE,
        related_name='availabilities'
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Availabilities"
        ordering = ['day_of_week', 'start_time']
        unique_together = ['therapist', 'day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.therapist.name} - {self.get_day_of_week_display()} {self.start_time.strftime('%I:%M %p')}-{self.end_time.strftime('%I:%M %p')}"
    
    def get_duration_minutes(self):
        """Get duration in minutes"""
        start = timezone.datetime.combine(timezone.now().date(), self.start_time)
        end = timezone.datetime.combine(timezone.now().date(), self.end_time)
        duration = end - start
        return int(duration.total_seconds() / 60)


class TimeOff(models.Model):
    """Expert time off requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name='time_offs'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Time Off"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.therapist.name} - {self.start_date} to {self.end_date} ({self.status})"
    
    @property
    def is_approved(self):
        return self.status == 'approved'


# In expert/models.py

class TimeSlot(models.Model):
    """Individual time slots that can be booked (like cinema seats)"""
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name='time_slots'
    )
    availability = models.ForeignKey(
        'Availability',
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_slots'
    )
    
    # Slot details
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.IntegerField(default=90)
    
    # Status flags (like cinema seats)
    is_available = models.BooleanField(default=True)  # Available for booking
    is_booked = models.BooleanField(default=False)    # Already booked
    is_blocked = models.BooleanField(default=False)   # Manually blocked by therapist
    
    # Booking reference - CHANGE THIS LINE
    booking = models.OneToOneField(
        'user.SessionBooking',  # Changed from 'Booking' to 'user.SessionBooking'
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booked_slot'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Time Slots"
        ordering = ['date', 'start_time']
        unique_together = ['therapist', 'date', 'start_time']  # Prevent duplicate slots
        indexes = [
            models.Index(fields=['therapist', 'date', 'is_available']),
            models.Index(fields=['therapist', 'date', 'is_booked']),
            models.Index(fields=['date', 'is_available']),
        ]
    
    def __str__(self):
        status = "Booked" if self.is_booked else "Blocked" if self.is_blocked else "Available"
        return f"{self.therapist.name} - {self.date.strftime('%b %d, %Y')} {self.start_time.strftime('%I:%M %p')}-{self.end_time.strftime('%I:%M %p')} ({status})"
    
    @property
    def display_time(self):
        """Get formatted time range"""
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"
    
    @property
    def display_date(self):
        """Get formatted date"""
        return self.date.strftime('%A, %B %d, %Y')
    
    @property
    def status_display(self):
        """Get status with emoji for display"""
        if self.is_booked:
            return {'text': 'Booked', 'icon': 'fa-solid fa-circle-check', 'color': '#dc3545'}
        elif self.is_blocked:
            return {'text': 'Unavailable', 'icon': 'fa-solid fa-ban', 'color': '#6c757d'}
        else:
            return {'text': 'Available', 'icon': 'fa-solid fa-circle', 'color': '#28a745'}
    
    def book(self, booking_instance):
        """Mark slot as booked (like seat taken)"""
        self.is_available = False
        self.is_booked = True
        self.booking = booking_instance
        self.save()
    
    def release(self):
        """Release a booked slot (like seat becomes available)"""
        self.is_available = True
        self.is_booked = False
        self.booking = None
        self.save()
    
    def block(self):
        """Manually block this slot (make unavailable)"""
        if not self.is_booked:
            self.is_available = False
            self.is_blocked = True
            self.save()
            return True
        return False
    
    def unblock(self):
        """Unblock this slot"""
        self.is_available = True
        self.is_blocked = False
        self.save()


class Booking(models.Model):
    """Session booking model"""
    BOOKING_STATUS = [
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]
    
    # Core relationships
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    seeker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seeker_bookings'
    )
    
    # Slot reference
    slot = models.OneToOneField(
        TimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        related_name='booking_detail'
    )
    
    # Booking details
    booking_date = models.DateTimeField(auto_now_add=True)
    session_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Status
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='confirmed')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Fees
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Meeting details
    meeting_link = models.URLField(blank=True)
    
    # Timestamps
    confirmed_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = "Bookings"
        ordering = ['-session_date', '-start_time']
        indexes = [
            models.Index(fields=['therapist', 'session_date']),
            models.Index(fields=['seeker', 'status']),
        ]
    
    def __str__(self):
        return f"Booking: {self.seeker.username} with {self.therapist.name} on {self.session_date} at {self.start_time}"
    
    def save(self, *args, **kwargs):
        if not self.total_amount and self.consultation_fee:
            self.total_amount = self.consultation_fee
        super().save(*args, **kwargs)
    
    @property
    def is_upcoming(self):
        """Check if booking is upcoming"""
        booking_datetime = timezone.datetime.combine(self.session_date, self.start_time)
        booking_datetime = timezone.make_aware(booking_datetime)
        return booking_datetime > timezone.now() and self.status == 'confirmed'
    
    def cancel_booking(self, reason=""):
        """Cancel the booking"""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()
        
        # Release the slot (like seat becomes available again)
        if self.slot:
            self.slot.release()
    
    def complete_booking(self):
        """Mark booking as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()


class TherapistSettings(models.Model):
    """Therapist consultation settings"""
    therapist = models.OneToOneField(
        Therapist,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    # Consultation settings
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    advance_booking_days = models.IntegerField(default=30, help_text="How far in advance clients can book")
    session_duration = models.IntegerField(default=90, help_text="Default session duration in minutes")
    buffer_time = models.IntegerField(default=15, help_text="Buffer time between sessions in minutes")
    
    # Features enabled
    video_enabled = models.BooleanField(default=True)
    chat_enabled = models.BooleanField(default=True)
    instant_booking = models.BooleanField(default=True)
    
    # Statistics (updated via signals/triggers)
    total_sessions = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Therapist Settings"
    
    def __str__(self):
        return f"{self.therapist.name}'s Settings"
    
    def update_stats(self):
        """Update therapist statistics"""
        completed_bookings = Booking.objects.filter(
            therapist=self.therapist,
            status='completed',
            payment_status='paid'
        )
        
        self.total_sessions = completed_bookings.count()
        
        earnings = completed_bookings.aggregate(total=Sum('consultation_fee'))['total']
        if earnings:
            self.total_earnings = earnings
        
        self.save()


# Signals to create settings when therapist is created
@receiver(post_save, sender=Therapist)
def create_therapist_settings(sender, instance, created, **kwargs):
    """Create TherapistSettings when a new Therapist is created"""
    if created:
        TherapistSettings.objects.create(therapist=instance)


# Signal to create ExpertProfileSettings when therapist is created
@receiver(post_save, sender=Therapist)
def create_expert_profile_settings(sender, instance, created, **kwargs):
    """Create ExpertProfileSettings when a new Therapist is created"""
    if created:
        ExpertProfileSettings.objects.create(therapist=instance)














# Add this to your expert/models.py file

# In expert/models.py
class ChatMessage(models.Model):
    """Model for chat messages between experts and users"""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_sent_messages'  # Unique, won't conflict
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expert_received_messages'  # Unique, won't conflict
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_admin_reply = models.BooleanField(default=False, help_text="True if expert replied")
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'timestamp']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"Expert Chat: {self.sender.username} to {self.recipient.username} at {self.timestamp}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
    
    @classmethod
    def get_conversation(cls, user1, user2):
        """Get all messages between two users"""
        return cls.objects.filter(
            models.Q(sender=user1, recipient=user2) |
            models.Q(sender=user2, recipient=user1)
        ).order_by('timestamp')
    
    @classmethod
    def get_unread_count(cls, user):
        """Get unread message count for a user"""
        return cls.objects.filter(recipient=user, is_read=False).count()
    
    @classmethod
    def mark_conversation_as_read(cls, user, other_user):
        """Mark all messages from other_user to user as read"""
        cls.objects.filter(
            sender=other_user,
            recipient=user,
            is_read=False
        ).update(is_read=True)


# expert/models.py - Add this new model

class SessionNote(models.Model):
    """Post-session notes, prescriptions, or recommendations from expert to user"""
    NOTE_TYPES = [
        ('prescription', 'Prescription'),
        ('recommendation', 'Recommendation'),
        ('exercise', 'Exercise/Homework'),
        ('referral', 'Referral'),
        ('follow_up', 'Follow-up Note'),
        ('general', 'General Note'),
    ]
    
    session = models.OneToOneField(
        'user.SessionBooking',
        on_delete=models.CASCADE,
        related_name='expert_notes'
    )
    therapist = models.ForeignKey(
        'user.Therapist',
        on_delete=models.CASCADE,
        related_name='session_notes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_session_notes'
    )
    
    # Note content
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='general')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # For prescriptions
    medication_name = models.CharField(max_length=200, blank=True, null=True)
    dosage = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.CharField(max_length=100, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    
    # For exercises/homework
    exercise_name = models.CharField(max_length=200, blank=True, null=True)
    exercise_instructions = models.TextField(blank=True, null=True)
    exercise_duration = models.CharField(max_length=100, blank=True, null=True)
    
    # Attachments
    attachment = models.FileField(upload_to='session_notes/%Y/%m/', blank=True, null=True)
    
    # Metadata
    is_read = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.get_note_type_display()} for {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


# Also add this signal to auto-create related objects
@receiver(post_save, sender='user.SessionBooking')
def create_session_note_placeholder(sender, instance, created, **kwargs):
    """This is just a placeholder - notes are created manually when completing sessions"""
    pass