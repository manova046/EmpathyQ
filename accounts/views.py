

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import timedelta
from django.contrib import messages
from .models import User, ExpertProfile
from .decorators import role_required



# Add this import at the top of accounts/views.py with your other imports
from expert.models import SessionNote

def user_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password1']
        email = request.POST.get('email', '')

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role=User.USER  # This is 'user' (lowercase)
        )

        login(request, user)
        return redirect('accounts:user_dashboard')

    return render(request, 'accounts/user_register.html')

def expert_register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password1']
        email = request.POST.get('email', '')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Please choose another.")
            return redirect('accounts:expert_register')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered. Please use another email or login.")
            return redirect('accounts:expert_register')
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                role=User.EXPERT
            )

            # Handle certificate upload
            certificate_file = request.FILES.get('certificate')
            additional_files = request.FILES.get('additional_documents')
            
            # Create expert profile
            expert_profile = ExpertProfile.objects.create(
                user=user,
                qualification=request.POST['qualification'],
                license_number=request.POST['license_number'],
                experience_years=request.POST['experience_years'],
                specialization=request.POST['specialization'],
                certificate=certificate_file,
                additional_documents=additional_files,
                is_approved=False
            )
            
            # AUTO-CREATE THERAPIST PROFILE
            from user.models import Therapist
            therapist = Therapist.objects.create(
                name=user.username,
                email=user.email,
                specialization=request.POST['specialization'],
                bio=f"Experienced professional specializing in {request.POST['specialization']}.",
                rating=4.8,
                total_sessions=0,
                is_available=True
            )
            print(f"✅ Auto-created therapist profile for {user.username}")

            messages.success(
                request,
                "Your profile has been submitted successfully! Our team will review your credentials and verify your license. You will receive an email notification once approved (usually within 2-3 business days)."
            )
            
            # Redirect to login page
            return redirect('accounts:login')
            
        except Exception as e:
            messages.error(request, f"An error occurred during registration: {str(e)}")
            # Delete user if created but profile failed
            if 'user' in locals():
                user.delete()
            return redirect('accounts:expert_register')

    return render(request, 'accounts/expert_register.html')





def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect('login')
        
        # ===== NEW: Check if user is blocked =====
        if user.is_blocked:
            # Store blocked reason in session for display
            request.session['blocked_reason'] = user.blocked_reason or "Your account has been blocked by an administrator."
            return redirect('accounts:blocked_page')

        # Expert approval check
        if user.role == User.EXPERT:
            # Check if expert profile exists and is approved
            if not hasattr(user, 'expert_profile'):
                messages.error(
                    request,
                    "Your expert profile is missing. Please contact support."
                )
                return redirect('login')
            
            if not user.expert_profile.is_approved:
                messages.error(
                    request,
                    "Your expert profile is pending admin approval. You will be notified once approved."
                )
                return redirect('login')
            
            # If approved, login and redirect to accounts expert dashboard
            login(request, user)
            print(f"DEBUG: Expert {user.username} logged in successfully")
            print(f"DEBUG: Redirecting to accounts:expert_dashboard")
            return redirect('accounts:expert_dashboard')
        
        # For non-expert users
        login(request, user)
        
        # DEBUG: Print user info
        print(f"DEBUG: User {user.username} logged in with role: {user.role}")
        print(f"DEBUG: Is superuser: {user.is_superuser}")
        
        # Role-based redirect for other users
        if user.is_superuser:
            print(f"DEBUG: Redirecting to admin_dashboard")
            return redirect('accounts:admin_dashboard')
        elif user.role == User.USER:
            print(f"DEBUG: Redirecting to user_dashboard")
            return redirect('accounts:user_dashboard')
        else:
            print(f"DEBUG: Default redirect to user_dashboard")
            return redirect('accounts:user_dashboard')

    return render(request, 'accounts/login.html')


# ===== NEW: Blocked page view =====
def blocked_page(request):
    """Display blocked page for users who are blocked"""
    reason = request.session.get('blocked_reason', 'Your account has been blocked by an administrator.')
    return render(request, 'accounts/blocked.html', {'blocked_reason': reason})


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth import get_user_model

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from user.models import EmotionalCheckIn, EmotionalTask


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from user.models import EmotionalCheckIn, EmotionalTask

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from user.models import (
    EmotionalCheckIn,
    UserTaskAssignment,
    SessionBooking
)




@login_required
def user_dashboard(request):
    """User dashboard with recent check-ins and tasks"""
    
    # ==============================
    # Last Emotional Check-in
    # ==============================
    last_checkin = (
        EmotionalCheckIn.objects
        .filter(user=request.user)
        .order_by("-created_at")
        .first()
    )

    # ==============================
    # Task Assignments
    # ==============================
    assignments = UserTaskAssignment.objects.filter(
        user=request.user
    ).select_related("task")

    total_tasks = assignments.count()
    completed_tasks_count = assignments.filter(completed_at__isnull=False).count()
    pending_tasks_count = assignments.filter(completed_at__isnull=True).count()

    # Show only recent 5 tasks on dashboard
    recent_assignments = assignments.order_by("-assigned_at")[:5]
    
    # For the recommended tasks section (pending tasks only)
    pending_tasks = assignments.filter(completed_at__isnull=True).order_by("-assigned_at")[:10]

    # ==============================
    # Emotional Check-in Stats
    # ==============================
    checkin_count = EmotionalCheckIn.objects.filter(
        user=request.user
    ).count()
    
    # Get recent check-ins for display
    recent_checkins = EmotionalCheckIn.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    # ==============================
    # Upcoming Sessions
    # ==============================
    upcoming_sessions_count = SessionBooking.objects.filter(
        user=request.user,
        booking_date__gte=timezone.now().date(),
        status__in=["pending", "confirmed"]
    ).count()
    
    # Get completed tasks
    completed_tasks = assignments.filter(completed_at__isnull=False).order_by('-completed_at')[:5]

    # ==============================
    # Completion Rate
    # ==============================
    completion_rate = 0
    if total_tasks > 0:
        completion_rate = int((completed_tasks_count / total_tasks) * 100)

    # ==============================
    # Calculate Streak (FIXED)
    # ==============================
    today = timezone.now().date()
    streak = 0
    
    # Get all check-in dates ordered by most recent
    checkins = EmotionalCheckIn.objects.filter(
        user=request.user
    ).order_by('-created_at').values_list('created_at', flat=True)
    
    if checkins:
        current_date = today
        for checkin_date in checkins:
            checkin_date = checkin_date.date()
            if checkin_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif checkin_date < current_date:
                # Break if we find a gap in the streak
                break

    # ==============================
    # ADD NOTES DATA FOR DASHBOARD
    # ==============================
    from expert.models import SessionNote
    
    # Get all notes for the current user
    user_notes = SessionNote.objects.filter(
        user=request.user
    ).select_related('therapist').order_by('-created_at')
    
    # Calculate note statistics
    total_count = user_notes.count()
    unread_count = user_notes.filter(is_read=False).count()
    
    # Get recent notes (first 3)
    recent_notes = user_notes[:3]
    
    # Get counts by type
    prescription_count = user_notes.filter(note_type='prescription').count()
    recommendation_count = user_notes.filter(note_type='recommendation').count()
    exercise_count = user_notes.filter(note_type='exercise').count()

    # ==============================
    # Render Dashboard
    # ==============================
    return render(
        request,
        "accounts/user.html",
        {
            # Last check-in
            "last_checkin": last_checkin,
            
            # Check-in stats
            "checkin_count": checkin_count,
            "recent_checkins": recent_checkins,
            
            # Task stats (for the progress card)
            "total_tasks": total_tasks,
            "completed_tasks_count": completed_tasks_count,
            "pending_tasks_count": pending_tasks_count,
            "completion_rate": completion_rate,
            
            # Task lists (for the tasks section)
            "tasks": pending_tasks,  # This is what your template uses
            "pending_tasks": pending_tasks,
            "recent_assignments": recent_assignments,
            "completed_tasks": completed_tasks,
            
            # Session stats
            "upcoming_sessions_count": upcoming_sessions_count,
            
            # Streak
            "streak": streak,
            
            # Current date
            "current_date": timezone.now(),
            
            # ===== NOTES DATA =====
            "total_count": total_count,
            "unread_count": unread_count,
            "recent_notes": recent_notes,
            "prescription_count": prescription_count,
            "recommendation_count": recommendation_count,
            "exercise_count": exercise_count,
        }
    )


# In accounts/views.py - update expert_dashboard function
@login_required
@role_required([User.EXPERT])
def expert_dashboard(request):
    """Expert dashboard with session statistics"""
    from django.utils import timezone
    from user.models import SessionBooking, Therapist
    from expert.models import ExpertProfileSettings
    from accounts.models import ChatMessage  # Add this import
    
    print(f"DEBUG expert_dashboard: User {request.user.username} with role {request.user.role}")
    
    # Get the therapist profile for this user
    try:
        # Try to find therapist by name (matching the user's username or full name)
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        
        # Get or create profile settings
        profile_settings, created = ExpertProfileSettings.objects.get_or_create(therapist=therapist)
        
        # Get counts for different session statuses
        pending_count = SessionBooking.objects.filter(
            therapist=therapist,
            status='pending'
        ).count()
        
        upcoming_count = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date__gte=timezone.now().date(),
            status='confirmed'
        ).count()
        
        completed_count = SessionBooking.objects.filter(
            therapist=therapist,
            status='completed'
        ).count()
        
        # Get today's sessions count
        today_sessions_count = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date=timezone.now().date(),
            status__in=['confirmed', 'pending']
        ).count()
        
        # Get recent bookings for the activity section
        recent_bookings = SessionBooking.objects.filter(
            therapist=therapist
        ).order_by('-booking_date', '-booking_time')[:5]
        
        # Safely get consultation fee
        fee = 50  # default
        if profile_settings and hasattr(profile_settings, 'consultation_fee') and profile_settings.consultation_fee:
            fee = profile_settings.consultation_fee
        
        # Calculate total earnings
        total_earnings = completed_count * fee
        
        # Calculate profile completion percentage
        profile_completion = calculate_profile_completion(therapist, profile_settings)
        
        # Get unread chat count using ChatMessage model
        unread_chat_count = ChatMessage.objects.filter(
            recipient=request.user,
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        # Get latest unread message for preview
        latest_unread_message = ChatMessage.objects.filter(
            recipient=request.user,
            is_read=False
        ).exclude(
            sender=request.user
        ).select_related('sender').order_by('-timestamp').first()
        
    except Therapist.DoesNotExist:
        # If therapist profile doesn't exist, set all counts to 0
        pending_count = 0
        upcoming_count = 0
        completed_count = 0
        today_sessions_count = 0
        recent_bookings = []
        total_earnings = 0
        profile_completion = 0
        profile_settings = None
        therapist = None
        unread_chat_count = 0
        latest_unread_message = None
        print(f"DEBUG: Therapist profile not found for user {request.user.username}")
    
    context = {
        'pending_count': pending_count,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'total_earnings': total_earnings,
        'today_sessions_count': today_sessions_count,
        'recent_bookings': recent_bookings,
        'profile': profile_settings,
        'profile_completion': profile_completion,
        'therapist': therapist,
        'unread_chat_count': unread_chat_count,
        'latest_unread_message': latest_unread_message,
    }
    # FIXED: Removed the extra closing parenthesis
    return render(request, 'accounts/expert.html', context)












def calculate_profile_completion(therapist, profile_settings):
    """Calculate profile completion percentage"""
    if not therapist or not profile_settings:
        return 0
    
    total_fields = 0
    completed_fields = 0
    
    # Check Therapist fields that actually exist in your model
    if hasattr(therapist, 'specialization') and therapist.specialization:
        completed_fields += 1
    total_fields += 1
    
    if hasattr(therapist, 'bio') and therapist.bio:
        completed_fields += 1
    total_fields += 1
    
    # Check if therapist has any experience field (using a safe approach)
    # Since experience_years doesn't exist, we'll check for a different field or skip it
    # For now, we'll just count it as not applicable
    # You can add other fields that exist in your Therapist model here
    
    # Check Profile Settings fields
    if hasattr(profile_settings, 'consultation_fee') and profile_settings.consultation_fee:
        completed_fields += 1
    total_fields += 1
    
    if hasattr(profile_settings, 'languages') and profile_settings.languages:
        completed_fields += 1
    total_fields += 1
    
    if hasattr(profile_settings, 'qualifications') and profile_settings.qualifications:
        completed_fields += 1
    total_fields += 1
    
    if hasattr(profile_settings, 'about_me') and profile_settings.about_me:
        completed_fields += 1
    total_fields += 1
    
    return int((completed_fields / total_fields) * 100) if total_fields > 0 else 0

def is_admin(user):
    # Simplified: Only superusers can access admin dashboard
    return user.is_authenticated and user.is_superuser



@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get pending and approved experts
    pending_experts = ExpertProfile.objects.filter(is_approved=False).order_by('-uploaded_at')
    approved_experts = ExpertProfile.objects.filter(is_approved=True).order_by('-uploaded_at')[:5]
    
    # Get ALL experts (for the experts list section)
    all_experts = ExpertProfile.objects.all().order_by('-uploaded_at').select_related('user')
    
    # Get ALL users (for the users list) - FIXED: Only regular users, no experts
    regular_users = User.objects.filter(
        role=User.USER  # Only users with role='user'
    ).exclude(
        is_superuser=True  # Exclude superusers/admins
    ).order_by('-date_joined')
    
    # Get counts for statistics
    pending_count = pending_experts.count()
    approved_count = ExpertProfile.objects.filter(is_approved=True).count()
    total_experts = User.objects.filter(role=User.EXPERT).count()
    total_users = regular_users.count()  # Count only regular users
    
    # Get unread chat messages count
    unread_chat_count = ChatMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # Get latest unread message for preview
    latest_unread_message = ChatMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).select_related('sender').order_by('-timestamp').first()
    
    # Get all incoming messages (for the inbox section)
    all_incoming_messages = ChatMessage.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-timestamp')[:20]  # Last 20 messages
    
    context = {
        # Existing data
        'pending_experts': pending_experts,
        'approved_experts': approved_experts,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_experts': total_experts,
        'total_users': total_users,
        
        # New data for experts list
        'all_experts': all_experts,
        
        # FIXED: Regular users only (no experts)
        'regular_users': regular_users,
        'regular_users_count': regular_users.count(),
        
        # Chat notification data
        'unread_chat_count': unread_chat_count,
        'latest_unread_message': latest_unread_message,
        'all_incoming_messages': all_incoming_messages,
    }
    return render(request, "accounts/admin.html", context)

@login_required
@user_passes_test(is_admin)
def approve_expert(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    expert.is_approved = True
    expert.save()
    messages.success(request, f"Expert {expert.user.username} has been approved.")
    return redirect("accounts:admin_dashboard")

@login_required
@user_passes_test(is_admin)
def reject_expert(request, expert_id):
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    username = expert.user.username
    expert.user.delete()
    messages.success(request, f"Expert {username} has been rejected and removed.")
    return redirect("accounts:admin_dashboard")

def index(request):
    return render(request, "accounts/index.html")



# accounts/views.py
from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('accounts:login')




# Add these imports at the top
from django.db.models import Q, Count
from .models import ChatMessage

@login_required
@user_passes_test(is_admin)
def admin_chat(request):
    """Admin chat interface to communicate with users"""
    
    # Get all conversations (users who have sent messages or been replied to)
    conversations = []
    
    # Get all messages where admin is sender or recipient
    admin_messages = ChatMessage.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('sender', 'recipient')
    
    # Get unique users (excluding admin)
    user_ids = set()
    for msg in admin_messages:
        if msg.sender != request.user:
            user_ids.add(msg.sender.id)
        if msg.recipient != request.user:
            user_ids.add(msg.recipient.id)
    
    # Build conversation list for each user
    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            
            # Get last message between admin and this user
            last_msg = ChatMessage.objects.filter(
                Q(sender=request.user, recipient=user) |
                Q(sender=user, recipient=request.user)
            ).order_by('-timestamp').first()
            
            # Count unread messages from this user
            unread_count = ChatMessage.objects.filter(
                sender=user,
                recipient=request.user,
                is_read=False
            ).count()
            
            conversations.append({
                'user': user,
                'last_message': last_msg.message if last_msg else '',
                'last_time': last_msg.timestamp if last_msg else None,
                'unread_count': unread_count,
            })
            
        except User.DoesNotExist:
            continue
    
    # Sort by most recent message
    conversations.sort(key=lambda x: x['last_time'] or datetime.min, reverse=True)
    
    # Handle specific user selection
    active_user_id = request.GET.get('user')
    active_user = None
    chat_messages = []
    
    if active_user_id:
        try:
            active_user = User.objects.get(id=active_user_id)
            
            # Get messages between admin and this user
            chat_messages = ChatMessage.objects.filter(
                Q(sender=request.user, recipient=active_user) |
                Q(sender=active_user, recipient=request.user)
            ).order_by('timestamp')
            
            # Mark messages as read
            chat_messages.filter(
                sender=active_user,
                recipient=request.user,
                is_read=False
            ).update(is_read=True)
            
        except User.DoesNotExist:
            pass
    
    # Handle POST request (sending message)
    if request.method == 'POST':
        recipient_id = request.POST.get('recipient_id')
        message_text = request.POST.get('message')
        
        if recipient_id and message_text:
            try:
                recipient = User.objects.get(id=recipient_id)
                
                # Create message
                ChatMessage.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    message=message_text,
                    is_admin_reply=True
                )
                
                messages.success(request, f'Reply sent to {recipient.username}')
                return redirect(f"{request.path}?user={recipient_id}")
                
            except User.DoesNotExist:
                messages.error(request, 'User not found')
    
    context = {
        'conversations': conversations,
        'active_user': active_user,
        'chat_messages': chat_messages,
    }
    return render(request, 'accounts/admin_chat.html', context)







# Add these imports at the top
from django.utils import timezone
from django.http import JsonResponse

# ===== NEW: Block/Unblock User Functions =====
@login_required
@user_passes_test(is_admin)
def block_user(request, user_id):
    """Block a user with a reason"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        reason = request.POST.get('reason', '')
        
        # Prevent blocking self
        if user == request.user:
            messages.error(request, "You cannot block yourself!")
            return redirect('accounts:admin_dashboard')
        
        # Block the user
        user.block(request.user, reason)
        
        # Create notification (optional)
        from .models import BlockedUserNotification
        BlockedUserNotification.objects.create(
            user=user,
            message=f"Your account has been blocked. Reason: {reason}",
            sent_by=request.user
        )
        
        messages.success(request, f"User {user.username} has been blocked successfully.")
        return redirect('accounts:admin_dashboard')
    
    return redirect('accounts:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def unblock_user(request, user_id):
    """Unblock a user"""
    user = get_object_or_404(User, id=user_id)
    user.unblock()
    messages.success(request, f"User {user.username} has been unblocked.")
    return redirect('accounts:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def block_expert(request, expert_id):
    """Block an expert (by expert profile ID)"""
    if request.method == 'POST':
        expert = get_object_or_404(ExpertProfile, id=expert_id)
        user = expert.user
        reason = request.POST.get('reason', '')
        
        # Prevent blocking self
        if user == request.user:
            messages.error(request, "You cannot block yourself!")
            return redirect('accounts:admin_dashboard')
        
        # Block the user
        user.block(request.user, reason)
        
        # Create notification
        from .models import BlockedUserNotification
        BlockedUserNotification.objects.create(
            user=user,
            message=f"Your expert account has been blocked. Reason: {reason}",
            sent_by=request.user
        )
        
        messages.success(request, f"Expert {user.username} has been blocked successfully.")
        return redirect('accounts:admin_dashboard')
    
    return redirect('accounts:admin_dashboard')


@login_required
@user_passes_test(is_admin)
def unblock_expert(request, expert_id):
    """Unblock an expert (by expert profile ID)"""
    expert = get_object_or_404(ExpertProfile, id=expert_id)
    user = expert.user
    user.unblock()
    messages.success(request, f"Expert {user.username} has been unblocked.")
    return redirect('accounts:admin_dashboard')


# ===== NEW: AJAX endpoint for block reason modal =====
@login_required
@user_passes_test(is_admin)
def get_block_info(request, user_id):
    """Get user info for block modal (AJAX)"""
    user = get_object_or_404(User, id=user_id)
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_blocked': user.is_blocked,
        'blocked_reason': user.blocked_reason,
        'blocked_at': user.blocked_at.strftime('%Y-%m-%d %H:%M') if user.blocked_at else None,
        'blocked_by': user.blocked_by.username if user.blocked_by else None,
    }
    return JsonResponse(data)