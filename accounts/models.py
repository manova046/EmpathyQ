from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER = 'user'
    EXPERT = 'expert'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (USER, 'User'),
        (EXPERT, 'Expert'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=USER
    )
    
    # ===== NEW: Blocked user functionality =====
    is_blocked = models.BooleanField(default=False, help_text="Designates whether the user is blocked by admin")
    blocked_reason = models.TextField(blank=True, null=True, help_text="Reason for blocking the user")
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='blocked_users')

    def __str__(self):
        status = " (Blocked)" if self.is_blocked else ""
        return f"{self.username} ({self.role}){status}"

    def save(self, *args, **kwargs):
        # Automatically set admin role for superusers
        if self.is_superuser:
            self.role = self.ADMIN
        super().save(*args, **kwargs)
    
    # ===== NEW: Helper methods for blocking =====
    def block(self, admin_user, reason=""):
        """Block this user"""
        from django.utils import timezone
        self.is_blocked = True
        self.blocked_reason = reason
        self.blocked_at = timezone.now()
        self.blocked_by = admin_user
        self.save()
    
    def unblock(self):
        """Unblock this user"""
        self.is_blocked = False
        self.blocked_reason = None
        self.blocked_at = None
        self.blocked_by = None
        self.save()
    
    @property
    def is_active_user(self):
        """Check if user can login (not blocked and active)"""
        return self.is_active and not self.is_blocked


class ExpertProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="expert_profile"
    )

    qualification = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    experience_years = models.PositiveIntegerField()
    specialization = models.CharField(max_length=100)
    is_approved = models.BooleanField(default=False)
    
    # New fields for certificate uploads
    certificate = models.FileField(upload_to='expert_certificates/', blank=True, null=True)
    additional_documents = models.FileField(upload_to='expert_documents/', blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        status = " (Approved)" if self.is_approved else " (Pending)"
        return f"{self.user.username}{status}"


# Add this to your accounts/models.py
class ChatMessage(models.Model):
    """Model for storing chat messages between users and admin"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_admin_reply = models.BooleanField(default=False)
    
    # For grouping conversations
    conversation_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"From {self.sender.username}: {self.message[:50]}"
    
    def save(self, *args, **kwargs):
        # Create a unique conversation ID if not set
        if not self.conversation_id and self.recipient:
            # Sort user IDs to create consistent conversation ID
            user_ids = sorted([str(self.sender.id), str(self.recipient.id)])
            self.conversation_id = '_'.join(user_ids)
        super().save(*args, **kwargs)


# ===== NEW: Blocked User Notification Model (Optional) =====
class BlockedUserNotification(models.Model):
    """Store notifications sent to blocked users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='block_notifications')
    message = models.TextField()
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_block_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:50]}"