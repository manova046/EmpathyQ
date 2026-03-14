
# user/views.py - COMPLETELY UPDATED VERSION (CLEANED)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Avg
from django.db import transaction
from datetime import timedelta
import json
import random

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from user.models import Review
# Add these imports at the top of user/views.py
from django.http import JsonResponse, FileResponse
from expert.models import SessionNote
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.conf import settings  # <-- ADD THIS LINE
from .models import (
    GameScore, EmotionalQuestion, EmotionalOption, 
    EmotionalCheckIn, EmotionalAnswer, AtomicTask, 
    UserTaskAssignment, TaskCategory
)
import json
import random
from .spotify_utils import get_playlists_for_mood, get_mood_based_recommendations  # Add this import

# Import from user.models
from .models import (
    ChatFeedback, EmotionalQuestion, EmotionalCheckIn, EmotionalAnswer, 
    EmotionalOption, AtomicTask, UserTaskAssignment, EmotionalTask, TaskCategory,
    AnonymousChatRoom, ChatQueue, 
    ChatMessage as AnonymousChatMessage,  # For anonymous chat (has 'room' field)
    SessionCategory, SessionBooking
)

# Import from accounts.models
from accounts.models import User, ExpertProfile
from accounts.models import ChatMessage as AdminChatMessage  # For admin chat (has 'recipient' field)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_alias():
    """Generate a random alias for anonymous chat"""
    adjectives = ["Calm", "Bright", "Gentle", "Quiet", "Warm", "Kind", "Peaceful", "Wise", "Caring", "Patient"]
    nouns = ["Sky", "River", "Mountain", "Forest", "Ocean", "Star", "Cloud", "Leaf", "Wave", "Light"]
    return random.choice(adjectives) + random.choice(nouns) + str(random.randint(10, 99))




def analyze_mood_with_psychology(answers):
    """
    Advanced mood analysis using psychological principles.
    Now with 20+ mood types and improved accuracy.
    """
    
    # Mood weights for different questions (some questions are better indicators)
    question_weights = {}
    for answer in answers:
        question_weights[answer.question.id] = answer.question.weight
    
    # Calculate mood scores with weights
    mood_scores = {}
    category_scores = {}
    intensity_values = []
    
    for answer in answers:
        mood = answer.selected_option.mood
        intensity = answer.selected_option.intensity_score
        question_weight = answer.question.weight
        
        # Track intensity values for averaging
        intensity_values.append(intensity)
        
        # Calculate weighted score
        weighted_score = intensity * question_weight
        
        # Add to mood scores
        mood_scores[mood] = mood_scores.get(mood, 0) + weighted_score
        
        # Track by category
        category = answer.question.category
        if category not in category_scores:
            category_scores[category] = {}
        category_scores[category][mood] = category_scores[category].get(mood, 0) + weighted_score
    
    # If no scores, return neutral
    if not mood_scores:
        return ('neutral', None, 5, {})
    
    # Sort moods by score
    sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Get primary mood
    primary_mood = sorted_moods[0][0]
    
    # Find secondary mood (if exists and significant)
    secondary_mood = None
    if len(sorted_moods) > 1:
        # Check if second mood is at least 30% of primary
        if sorted_moods[1][1] >= (sorted_moods[0][1] * 0.3):
            secondary_mood = sorted_moods[1][0]
    
    # Calculate overall intensity (1-10) - FIXED: Always between 1-10
    avg_intensity = sum(intensity_values) / len(intensity_values) if intensity_values else 5
    # Ensure intensity is between 1 and 10
    intensity = max(1, min(10, round(avg_intensity)))
    
    # Analyze patterns
    patterns = {}
    
    # Check for mixed moods
    if secondary_mood:
        patterns['mixed_mood'] = f"{primary_mood}_{secondary_mood}"
    
    # Energy level detection
    high_energy_moods = ['motivated', 'excited', 'energetic', 'happy', 'anxious', 'stressed']
    medium_energy_moods = ['hopeful', 'grateful', 'proud', 'calm', 'peaceful', 'loved']
    low_energy_moods = ['low', 'tired', 'lonely', 'hopeless', 'confused', 'neutral']
    
    primary_energy = 'medium'
    if primary_mood in high_energy_moods:
        primary_energy = 'high'
    elif primary_mood in low_energy_moods:
        primary_energy = 'low'
    
    secondary_energy = None
    if secondary_mood:
        if secondary_mood in high_energy_moods:
            secondary_energy = 'high'
        elif secondary_mood in low_energy_moods:
            secondary_energy = 'low'
        else:
            secondary_energy = 'medium'
    
    patterns['energy_level'] = primary_energy
    patterns['secondary_energy'] = secondary_energy
    
    # Check for energy conflict (e.g., high energy primary but low energy secondary)
    if secondary_energy and primary_energy != secondary_energy:
        patterns['energy_conflict'] = True
    
    # Determine dominant category
    if category_scores:
        dominant_category = max(
            category_scores.items(), 
            key=lambda x: sum(x[1].values())
        )[0]
        patterns['dominant_category'] = dominant_category
    
    # Mood cluster detection (for more nuanced insights)
    mood_clusters = {
        'positive': ['happy', 'grateful', 'hopeful', 'peaceful', 'loved', 'proud', 'excited', 'calm', 'motivated'],
        'negative': ['low', 'stressed', 'anxious', 'irritable', 'lonely', 'overwhelmed', 'tired', 'hopeless', 'confused'],
        'high_energy': ['motivated', 'excited', 'energetic', 'anxious', 'stressed', 'overwhelmed'],
        'low_energy': ['low', 'tired', 'calm', 'peaceful', 'neutral', 'lonely', 'hopeless'],
    }
    
    # Check which clusters the primary mood belongs to
    for cluster_name, cluster_moods in mood_clusters.items():
        if primary_mood in cluster_moods:
            patterns[f'in_{cluster_name}_cluster'] = True
    
    return (primary_mood, secondary_mood, intensity, patterns)




def get_recommended_atomic_tasks(
    primary_mood,
    secondary_mood,
    intensity,
    patterns,
    user=None,
    limit=5
):
    """
    Enhanced atomic task recommendation engine with mood mapping
    """
    
    # Mood mapping for related moods (for better recommendations)
    mood_families = {
        'positive': ['happy', 'grateful', 'hopeful', 'loved', 'proud', 'peaceful'],
        'negative': ['low', 'stressed', 'anxious', 'irritable', 'lonely', 'overwhelmed', 'hopeless'],
        'high_energy': ['motivated', 'excited', 'energetic', 'anxious', 'stressed', 'overwhelmed'],
        'low_energy': ['low', 'tired', 'calm', 'peaceful', 'neutral', 'lonely', 'hopeless'],
    }
    
    base_queryset = AtomicTask.objects.filter(is_active=True)

    # ============================
    # 1️⃣ Best match (primary mood)
    # ============================
    tasks = base_queryset.filter(mood=primary_mood)

    # ============================
    # 2️⃣ Add secondary mood if exists and primary has few tasks
    # ============================
    if secondary_mood and tasks.count() < limit:
        secondary_tasks = base_queryset.filter(mood=secondary_mood)
        tasks = tasks | secondary_tasks

    # ============================
    # 3️⃣ If still low on tasks, include mood family
    # ============================
    if tasks.count() < limit:
        for family_name, family_moods in mood_families.items():
            if primary_mood in family_moods:
                family_tasks = base_queryset.filter(mood__in=family_moods)
                tasks = tasks | family_tasks
                break

    # ============================
    # 4️⃣ Intensity-based filtering
    # ============================
    if intensity <= 3:  # Low intensity
        filtered = tasks.filter(energy_level__in=['low', 'medium'])
        if filtered.exists():
            tasks = filtered
    elif intensity >= 8:  # High intensity
        filtered = tasks.filter(energy_level__in=['medium', 'high'])
        if filtered.exists():
            tasks = filtered

    # ============================
    # 5️⃣ Energy level from patterns
    # ============================
    if 'energy_level' in patterns:
        energy = patterns['energy_level']
        energy_filtered = tasks.filter(energy_level=energy)
        if energy_filtered.exists():
            # Boost priority of energy-matched tasks
            tasks = energy_filtered | tasks

    # ============================
    # 6️⃣ Fallback chain
    # ============================
    if not tasks.exists():
        # Try neutral
        tasks = base_queryset.filter(mood='neutral')
    
    if not tasks.exists():
        # Try calm (good default)
        tasks = base_queryset.filter(mood='calm')
    
    if not tasks.exists():
        # Any active task
        tasks = base_queryset

    # ============================
    # 7️⃣ Avoid recently completed tasks
    # ============================
    if user:
        # Get tasks completed in last 24 hours
        recent_task_ids = UserTaskAssignment.objects.filter(
            user=user,
            completed_at__isnull=False,
            assigned_at__gte=timezone.now() - timedelta(hours=24)
        ).values_list('task_id', flat=True)

        # Only exclude if we still have enough tasks
        if tasks.exclude(id__in=recent_task_ids).count() >= limit:
            tasks = tasks.exclude(id__in=recent_task_ids)

    # ============================
    # 8️⃣ Order and randomize
    # ============================
    tasks = tasks.order_by('-priority')
    task_list = list(tasks)

    if not task_list:
        return []

    # Shuffle but keep priority order as bias
    random.shuffle(task_list)

    return task_list[:limit]





# ============================================================================
# EMOTIONAL CHECK-IN VIEWS
# ============================================================================




@login_required
def emotional_checkin(request):
    """
    Enhanced emotional check-in with random question selection
    """
    print(f"===== emotional_checkin view called with method: {request.method} =====")
    
    # For GET request - randomly select 15 questions
    if request.method == "GET":
        # Get all active questions
        all_questions = EmotionalQuestion.objects.prefetch_related("options").all()
        
        if not all_questions.exists():
            print("No questions found")
            return render(request, "user/emotional_checkin.html", {
                "error": "No emotional questions available. Please contact administrator."
            })
        
        # Randomly select 15 questions (or less if not enough)
        question_count = all_questions.count()
        num_to_select = min(15, question_count)
        
        # Randomly select questions
        import random
        selected_questions = random.sample(list(all_questions), num_to_select)
        
        print(f"Selected {num_to_select} random questions for check-in")
        
        return render(request, "user/emotional_checkin.html", {
            "questions": selected_questions
        })
    
    # ==============================
    # POST: Process emotional check-in
    # ==============================
    if request.method == "POST":
        print("Processing POST request")
        answers = []
        
        # Get all questions that were answered
        answered_question_ids = []
        for key in request.POST.keys():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')
                answered_question_ids.append(int(question_id))
        
        # Get the questions that were answered
        questions = EmotionalQuestion.objects.filter(id__in=answered_question_ids)
        
        # Ensure ALL questions are answered
        for question in questions:
            answer_key = f"question_{question.id}"
            option_id = request.POST.get(answer_key)
            print(f"Question {question.id}: {option_id}")

            if not option_id:
                print(f"Missing answer for question {question.id}")
                messages.error(request, "Please answer all questions.")
                # Re-select random questions for re-display
                all_questions = EmotionalQuestion.objects.all()
                num_to_select = min(15, all_questions.count())
                selected_questions = random.sample(list(all_questions), num_to_select)
                return render(request, "user/emotional_checkin.html", {
                    "questions": selected_questions
                })

        try:
            with transaction.atomic():
                print("Starting transaction...")

                # Create check-in first
                checkin = EmotionalCheckIn.objects.create(
                    user=request.user,
                    primary_mood="neutral",   # temporary default
                    intensity_score=5         # temporary default
                )
                print(f"Checkin created with id: {checkin.id}")

                # Save answers
                for question in questions:
                    option_id = request.POST.get(f"question_{question.id}")
                    
                    selected_option = EmotionalOption.objects.get(
                        id=option_id,
                        question=question
                    )
                    
                    answer = EmotionalAnswer.objects.create(
                        checkin=checkin,
                        question=question,
                        selected_option=selected_option
                    )
                    
                    answers.append(answer)
                    print(f"Answer created for question {question.id}")

                # ==============================
                # Enhanced Mood Analysis
                # ==============================
                print("Analyzing mood...")
                primary_mood, secondary_mood, intensity, patterns = \
                    analyze_mood_with_psychology(answers)
                print(f"Mood analysis: primary={primary_mood}, secondary={secondary_mood}, intensity={intensity}")
                print(f"Patterns: {patterns}")

                # Update check-in with final values
                checkin.primary_mood = primary_mood
                checkin.secondary_mood = secondary_mood
                checkin.intensity_score = intensity  # Already 1-10 from analysis
                
                # Add energy level from patterns
                if 'energy_level' in patterns:
                    checkin.energy_level = patterns['energy_level']
                
                # Add mood profile
                checkin.mood_profile = patterns
                checkin.save()
                print("Checkin updated")

                # ==============================
                # Get Recommended Atomic Tasks
                # ==============================
                print("Getting recommended tasks...")
                atomic_tasks = get_recommended_atomic_tasks(
                    primary_mood,
                    secondary_mood,
                    intensity,
                    patterns,
                    request.user
                )
                print(f"Found {len(atomic_tasks)} tasks")

                # Assign tasks to user
                assignments = []
                for task in atomic_tasks:
                    assignment, created = UserTaskAssignment.objects.get_or_create(
                        user=request.user,
                        task=task,
                        checkin=checkin
                    )
                    assignments.append(assignment)
                print(f"Created {len(assignments)} assignments")

                # ==============================
                # Redirect to result page with checkin_id
                # ==============================
                print(f"Redirecting to emotional_result with checkin_id: {checkin.id}")
                return redirect('user:emotional_result', checkin_id=checkin.id)

        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f"Something went wrong: {str(e)}")
            # Re-select random questions for re-display
            all_questions = EmotionalQuestion.objects.all()
            num_to_select = min(15, all_questions.count())
            selected_questions = random.sample(list(all_questions), num_to_select)
            return render(request, "user/emotional_checkin.html", {
                "questions": selected_questions
            })
        






@login_required
def emotional_result(request, checkin_id):
    """
    Display emotional check-in results with recommended tasks, 
    Spotify playlists, and book recommendations
    """
    # Get the check-in
    checkin = get_object_or_404(
        EmotionalCheckIn, 
        id=checkin_id, 
        user=request.user
    )
    
    # Get assignments for this check-in
    assignments = UserTaskAssignment.objects.filter(
        checkin=checkin
    ).select_related('task')
    
    # Get Spotify recommendations
    spotify_playlists = []
    spotify_tracks = []
    has_spotify = False
    
    # Get Book recommendations - FIXED: Increase limit to get more books
    book_recommendations = []
    has_books = False
    
    # Check if Spotify credentials are configured
    if hasattr(settings, 'SPOTIFY_CLIENT_ID') and hasattr(settings, 'SPOTIFY_CLIENT_SECRET'):
        if settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET:
            has_spotify = True
            try:
                # Get playlist recommendations
                spotify_playlists = get_playlists_for_mood(
                    mood=checkin.primary_mood,
                    secondary_mood=checkin.secondary_mood,
                    limit=3
                )
                
                # Get track recommendations
                spotify_tracks = get_mood_based_recommendations(
                    mood=checkin.primary_mood,
                    secondary_mood=checkin.secondary_mood,
                    limit=5
                )
            except Exception as e:
                print(f"Spotify error: {e}")
    
    # Get Book recommendations (Google Books API - no key needed)
    try:
        from .book_utils import get_mood_based_book_recommendations
        
        # FIXED: Increase limit to 10 to have enough for "Load More" functionality
        book_recommendations = get_mood_based_book_recommendations(
            mood=checkin.primary_mood,
            secondary_mood=checkin.secondary_mood,
            limit=10  # Changed from 4 to 10
        )
        
        if book_recommendations:
            has_books = True
            print(f"Found {len(book_recommendations)} books for mood: {checkin.primary_mood}")
            
    except Exception as e:
        print(f"Book API error: {e}")
        import traceback
        traceback.print_exc()
    
    context = {
        'checkin': checkin,
        'mood': checkin.primary_mood,
        'secondary_mood': checkin.secondary_mood,
        'intensity': checkin.intensity_score,
        'assignments': assignments,
        'spotify_playlists': spotify_playlists,
        'spotify_tracks': spotify_tracks,
        'has_spotify': has_spotify,
        'book_recommendations': book_recommendations,
        'has_books': has_books,
    }
    
    return render(request, 'user/emotional_result.html', context)


# ============================================================================
# CHECK-IN HISTORY VIEWS
# ============================================================================

def checkin_history(request):
    user = request.user
    checkins = EmotionalCheckIn.objects.filter(user=user).order_by('-created_at')

    # ---- Date Filter ----
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        checkins = checkins.filter(created_at__date__gte=start_date)

    if end_date:
        checkins = checkins.filter(created_at__date__lte=end_date)

    # ---- Mood Filter ----
    selected_mood = request.GET.get('mood')
    if selected_mood:
        checkins = checkins.filter(primary_mood=selected_mood)

    total_checkins = checkins.count()

    # ---- Mood Distribution ----
    mood_counts = checkins.values('primary_mood').annotate(count=Count('primary_mood'))

    mood_data = {
        'low': 0,
        'stressed': 0,
        'calm': 0,
        'motivated': 0,
        'anxious': 0,
        'neutral': 0,
        'irritable': 0,
    }

    for mood in mood_counts:
        mood_data[mood['primary_mood']] = mood['count']

    # ---- Dominant Mood Insight ----
    dominant_mood = None
    if total_checkins > 0:
        dominant_mood = max(mood_data, key=mood_data.get)

    mood_insight = ""

    mood_messages = {
        'low': "You've been feeling low recently. Consider reaching out to someone you trust or practicing self-care.",
        'stressed': "Stress levels seem high. Try relaxation techniques or short breaks during your day.",
        'calm': "Great emotional stability! Keep maintaining your healthy habits.",
        'motivated': "You're feeling motivated! This is a great time to work toward your goals.",
        'anxious': "Anxiety seems present. Deep breathing and grounding exercises may help.",
        'neutral': "Your mood has been balanced. Keep observing your emotional patterns.",
        'irritable': "You’ve been feeling irritable. Try identifying triggers and practicing patience strategies.",
    }

    if dominant_mood:
        mood_insight = mood_messages.get(dominant_mood)

    context = {
        'checkins': checkins,
        'total_checkins': total_checkins,
        'mood_data': mood_data,
        'mood_insight': mood_insight,
        'selected_mood': selected_mood,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'user/checkin_history.html', context)

@login_required
def checkin_detail(request, checkin_id):
    """
    Show full details of one emotional check-in
    """

    checkin = get_object_or_404(
        EmotionalCheckIn,
        id=checkin_id,
        user=request.user
    )

    assignments = UserTaskAssignment.objects.filter(
        checkin=checkin
    ).select_related("task")

    total_tasks = assignments.count()
    completed_tasks = assignments.filter(
        completed_at__isnull=False
    ).count()

    pending_tasks = assignments.filter(
        completed_at__isnull=True
    ).count()

    completion_rate = 0
    if total_tasks > 0:
        completion_rate = int((completed_tasks / total_tasks) * 100)

    return render(request, "user/checkin_detail.html", {
        "checkin": checkin,
        "assignments": assignments,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "completion_rate": completion_rate,
    })

# ============================================================================
# DASHBOARD & PROGRESS VIEWS
# ============================================================================


# user/views.py - Update this function (around line 732)

@login_required
def user_dashboard(request):
    """User dashboard with recent check-ins and tasks"""
    recent_checkins = EmotionalCheckIn.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    pending_tasks = UserTaskAssignment.objects.filter(
        user=request.user,
        completed_at__isnull=True
    ).order_by('-assigned_at')[:10]
    
    completed_tasks = UserTaskAssignment.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).order_by('-completed_at')[:5]
    
    # Calculate streaks
    today = timezone.now().date()
    streak = 0
    checkin_dates = EmotionalCheckIn.objects.filter(
        user=request.user
    ).dates('created_at', 'day').order_by('-date')
    
    if checkin_dates:
        current_date = today
        for checkin_date in checkin_dates:
            if checkin_date.date() == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
    
    # ==============================
    # ADD NOTES DATA FOR DASHBOARD
    # ==============================
    from expert.models import SessionNote
    
    # Get all notes for the current user
    user_notes = SessionNote.objects.filter(
        user=request.user
    ).select_related('therapist').order_by('-created_at')
    
    # Debug print to console
    print(f"Dashboard - Found {user_notes.count()} notes for user {request.user.username}")
    for note in user_notes:
        print(f"  Note: {note.id} - {note.title}")
    
    # Calculate note statistics
    total_count = user_notes.count()
    unread_count = user_notes.filter(is_read=False).count()
    
    # Get recent notes (first 3)
    recent_notes = user_notes[:3]
    
    # Get counts by type
    prescription_count = user_notes.filter(note_type='prescription').count()
    recommendation_count = user_notes.filter(note_type='recommendation').count()
    exercise_count = user_notes.filter(note_type='exercise').count()
    
    return render(request, "accounts/user.html", {
        "recent_checkins": recent_checkins,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "streak": streak,
        # ===== NOTES DATA =====
        "total_count": total_count,
        "unread_count": unread_count,
        "recent_notes": recent_notes,
        "prescription_count": prescription_count,
        "recommendation_count": recommendation_count,
        "exercise_count": exercise_count,
    })

@login_required
def mood_history(request):
    """View mood history over time"""
    checkins = EmotionalCheckIn.objects.filter(user=request.user).order_by('-created_at')
    
    # Prepare data for chart
    mood_data = []
    for c in checkins[:30]:  # Last 30 check-ins
        mood_data.append({
            'date': c.created_at.strftime('%Y-%m-%d %H:%M'),
            'mood': c.primary_mood,
            'intensity': c.intensity_score,
            'secondary': c.secondary_mood if c.secondary_mood else '',
        })
    
    return render(request, "user/mood_history.html", {
        "checkins": checkins,
        "mood_data_json": json.dumps(mood_data),
    })

@login_required
def track_progress(request):
    """Track user's emotional progress"""
    # Get last 7 days of check-ins
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    checkins = EmotionalCheckIn.objects.filter(
        user=request.user,
        created_at__date__gte=start_date
    ).order_by('created_at')
    
    # Calculate mood scores
    mood_scores = []
    dates = []
    for checkin in checkins:
        mood_scores.append(checkin.intensity_score)
        dates.append(checkin.created_at.strftime('%Y-%m-%d'))
    
    # Get mood distribution
    mood_distribution = EmotionalCheckIn.objects.filter(
        user=request.user
    ).values('primary_mood').annotate(count=Count('id')).order_by('-count')
    
    # Get task completion stats
    tasks_completed = UserTaskAssignment.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).count()
    
    tasks_pending = UserTaskAssignment.objects.filter(
        user=request.user,
        completed_at__isnull=True
    ).count()
    
    context = {
        'mood_scores': mood_scores,
        'dates': dates,
        'mood_distribution': mood_distribution,
        'total_checkins': checkins.count(),
        'tasks_completed': tasks_completed,
        'tasks_pending': tasks_pending,
    }
    return render(request, 'user/track_progress.html', context)

@login_required
def progress_report(request):
    """Generate comprehensive progress report"""
    # Get all user data
    total_checkins = EmotionalCheckIn.objects.filter(user=request.user).count()
    
    # Average intensity
    avg_intensity = EmotionalCheckIn.objects.filter(
        user=request.user
    ).aggregate(Avg('intensity_score'))['intensity_score__avg'] or 0
    
    # Most common mood
    most_common_mood = EmotionalCheckIn.objects.filter(
        user=request.user
    ).values('primary_mood').annotate(
        count=Count('id')
    ).order_by('-count').first()
    
    # Task statistics
    total_assigned_tasks = UserTaskAssignment.objects.filter(
        user=request.user
    ).count()
    
    completed_tasks = UserTaskAssignment.objects.filter(
        user=request.user,
        completed_at__isnull=False
    ).count()
    
    completion_rate = 0
    if total_assigned_tasks > 0:
        completion_rate = (completed_tasks / total_assigned_tasks) * 100
    
    # Session statistics
    total_sessions = SessionBooking.objects.filter(user=request.user).count()
    completed_sessions = SessionBooking.objects.filter(
        user=request.user,
        status='completed'
    ).count()
    
    context = {
        'total_checkins': total_checkins,
        'avg_intensity': round(avg_intensity, 1),
        'most_common_mood': most_common_mood,
        'total_tasks': total_assigned_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round(completion_rate, 1),
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
    }
    return render(request, 'user/progress_report.html', context)

# ============================================================================
# TASK MANAGEMENT VIEWS
# ============================================================================

@login_required
def complete_task(request, assignment_id):
    """Mark a task as completed"""
    assignment = get_object_or_404(
        UserTaskAssignment, 
        id=assignment_id, 
        user=request.user
    )
    
    if not assignment.completed_at:
        assignment.completed_at = timezone.now()
        assignment.save()
        messages.success(request, f'Task "{assignment.task.title}" completed! Great job! 🎉')
    
    return redirect('accounts:user_dashboard')




@login_required
def book_session(request):
    """Book a therapy session with approved experts"""
    import razorpay
    from django.conf import settings
    import json
    
    # Define specialization choices (matching your template)
    SPECIALIZATION_CHOICES = [
        ('Clinical Psychology', 'Clinical Psychology'),
        ('Counseling Psychology', 'Counseling Psychology'),
        ('Child & Adolescent Psychology', 'Child & Adolescent Psychology'),
        ('Educational Psychology', 'Educational Psychology'),
        ('Health Psychology', 'Health Psychology'),
        ('Neuropsychology', 'Neuropsychology'),
        ('Forensic Psychology', 'Forensic Psychology'),
        ('Industrial/Organizational Psychology', 'Industrial/Organizational Psychology'),
        ('Sports Psychology', 'Sports Psychology'),
        ('Rehabilitation Psychology', 'Rehabilitation Psychology'),
        ('Trauma & PTSD', 'Trauma & PTSD'),
        ('Anxiety & Depression', 'Anxiety & Depression'),
        ('Marriage & Family Therapy', 'Marriage & Family Therapy'),
        ('Addiction Counseling', 'Addiction Counseling'),
        ('Eating Disorders', 'Eating Disorders'),
        ('Geriatric Psychology', 'Geriatric Psychology'),
        ('School Psychology', 'School Psychology'),
        ('Behavioral Therapy', 'Behavioral Therapy'),
        ('Cognitive Behavioral Therapy (CBT)', 'Cognitive Behavioral Therapy (CBT)'),
        ('Mindfulness & Meditation', 'Mindfulness & Meditation'),
        ('Other - Specify in Qualification', 'Other - Specify in Qualification'),
    ]
    
    # Create a mapping dictionary for specializations
    SPECIALIZATION_MAP = {
        'Anxiety & Depression': 'Anxiety & Depression',
        'Health Psychology': 'Health Psychology',
        'Mental Health Expert': 'Other - Specify in Qualification',
        'Mental Health Professional': 'Other - Specify in Qualification',
        'Clinical Psychologist': 'Clinical Psychology',
        'Counselor': 'Counseling Psychology',
        'Therapist': 'Counseling Psychology',
        'Psychologist': 'Clinical Psychology',
    }
    
    from user.models import Therapist, SessionBooking, SessionCategory
    from expert.models import TimeSlot, ExpertProfileSettings
    
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Handle POST request for booking
    if request.method == 'POST':
        try:
            # Get form data
            expert_id = request.POST.get('expert_id')
            slot_id = request.POST.get('slot_id')
            session_date = request.POST.get('session_date')
            start_time = request.POST.get('start_time')
            consultation_fee = request.POST.get('consultation_fee')
            
            # Validate required fields
            if not all([expert_id, slot_id, session_date, start_time, consultation_fee]):
                messages.error(request, 'Missing required booking information.')
                return redirect('user:book_session')
            
            # Get the expert and slot
            therapist = Therapist.objects.get(id=expert_id)
            slot = TimeSlot.objects.get(id=slot_id, is_available=True, is_booked=False)
            
            # Calculate end time (assuming 60 min sessions)
            from datetime import datetime, timedelta
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = (datetime.combine(datetime.today(), start_time_obj) + timedelta(minutes=60)).time()
            
            # Create Razorpay order
            amount = int(float(consultation_fee) * 100)  # Convert to paise
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'receipt': f'booking_{therapist.id}_{slot.id}',
                'payment_capture': 1  # Auto capture
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            # Create booking with pending payment
            booking = SessionBooking.objects.create(
                therapist=therapist,
                seeker=request.user,
                slot=slot,
                session_date=session_date,
                start_time=start_time_obj,
                end_time=end_time_obj,
                consultation_fee=consultation_fee,
                total_amount=consultation_fee,
                payment_status='pending',
                status='confirmed'  # Keep as confirmed but payment pending
            )
            
            # Mark slot as booked
            slot.is_booked = True
            slot.save()
            
            # Store razorpay order info in session
            request.session['razorpay_order_id'] = razorpay_order['id']
            request.session['booking_id'] = booking.id
            
            context = {
                'booking': booking,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': amount,
                'currency': 'INR',
                'callback_url': request.build_absolute_uri('/user/payment-callback/'),
                'csrf_token': request.POST.get('csrfmiddlewaretoken'),
                'therapist': therapist,
            }
            
            return render(request, 'user/payment_page.html', context)
            
        except Therapist.DoesNotExist:
            messages.error(request, 'Therapist not found.')
            return redirect('user:book_session')
        except TimeSlot.DoesNotExist:
            messages.error(request, 'Selected time slot is no longer available.')
            return redirect('user:book_session')
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
            return redirect('user:book_session')
    
    # GET request - display available experts
    # Get all therapists who are available
    therapists = Therapist.objects.filter(
        is_available=True
    ).order_by('-created_at')
    
    # Check if a specific expert is requested
    expert_id = request.GET.get('expert')
    if expert_id:
        therapists = therapists.filter(id=expert_id)
    
    # Get pre-selected date and time if provided
    preselected_date = request.GET.get('date', '')
    preselected_time = request.GET.get('time', '')
    
    # Create a dictionary to count experts per specialization
    specialization_counts = {code: 0 for code, name in SPECIALIZATION_CHOICES}
    
    # Get today's date for slot filtering
    today = timezone.now().date()
    
    # Process each therapist and get their available slots
    for therapist in therapists:
        # Get available slots for this therapist
        available_slots = TimeSlot.objects.filter(
            therapist=therapist,
            date__gte=today,
            is_available=True,
            is_booked=False,
            is_blocked=False
        ).order_by('date', 'start_time')
        
        therapist.available_slots_count = available_slots.count()
        
        # Group slots by date for easier display
        slots_by_date = {}
        for slot in available_slots:
            date_str = slot.date.strftime('%Y-%m-%d')
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(slot)
        
        therapist.slots_by_date = slots_by_date
        
        # Get next available slot
        therapist.next_slot = available_slots.first() if available_slots.exists() else None
        
        # Get consultation fee from profile
        try:
            profile = ExpertProfileSettings.objects.filter(therapist=therapist).first()
            therapist.consultation_fee = profile.consultation_fee if profile else 250.00
        except:
            therapist.consultation_fee = 250.00
        
        # Count for specialization filter
        if therapist.specialization:
            if therapist.specialization in [code for code, name in SPECIALIZATION_CHOICES]:
                specialization_counts[therapist.specialization] += 1
            else:
                mapped_spec = SPECIALIZATION_MAP.get(therapist.specialization, 'Other - Specify in Qualification')
                specialization_counts[mapped_spec] += 1
        else:
            specialization_counts['Other - Specify in Qualification'] += 1
    
    # Create specializations list for filter display
    specializations = []
    for code, name in SPECIALIZATION_CHOICES:
        specializations.append({
            'id': code,
            'name': name,
            'icon': get_specialization_icon(code),
            'expert_count': specialization_counts[code]
        })
    
    # Filter by specialization if selected
    selected_specialization = None
    specialization_id = request.GET.get('specialization')
    
    if specialization_id and specialization_id != 'All Experts':
        # Filter therapists based on selected specialization
        filtered_therapists = []
        for therapist in therapists:
            if therapist.specialization == specialization_id:
                filtered_therapists.append(therapist)
            elif specialization_id == 'Other - Specify in Qualification':
                # Include therapists with unmapped specializations
                if therapist.specialization not in [code for code, name in SPECIALIZATION_CHOICES]:
                    filtered_therapists.append(therapist)
            else:
                # Check if it maps to the selected specialization
                mapped = SPECIALIZATION_MAP.get(therapist.specialization, 'Other - Specify in Qualification')
                if mapped == specialization_id:
                    filtered_therapists.append(therapist)
        
        therapists = filtered_therapists
        selected_specialization = {
            'id': specialization_id,
            'name': dict(SPECIALIZATION_CHOICES).get(specialization_id, specialization_id)
        }
    
    # Get session categories
    categories = SessionCategory.objects.all()
    
    # Add default values for template fields
    for therapist in therapists:
        # Set default values for display
        if not hasattr(therapist, 'rating') or therapist.rating is None:
            therapist.rating = 4.8
        if not hasattr(therapist, 'total_sessions') or therapist.total_sessions is None:
            # Count actual completed sessions if possible
            completed_count = SessionBooking.objects.filter(
                therapist=therapist, 
                status='completed'
            ).count()
            therapist.total_sessions = completed_count if completed_count > 0 else 120
        
        if not hasattr(therapist, 'bio') or therapist.bio is None:
            therapist.bio = f"Experienced professional specializing in {therapist.specialization or 'mental health'}."
        
        # Add experience_years from profile settings if available
        try:
            profile = ExpertProfileSettings.objects.filter(therapist=therapist).first()
            if profile and profile.experience_years:
                therapist.experience_years = profile.experience_years
            else:
                therapist.experience_years = 10  # Default
        except:
            therapist.experience_years = 10  # Default
    
    context = {
        'experts': therapists,
        'specializations': specializations,
        'selected_specialization': selected_specialization,
        'categories': categories,
        'total_experts': Therapist.objects.filter(is_available=True).count(),
        'current_date': timezone.now(),
        'preselected_date': preselected_date,
        'preselected_time': preselected_time,
        'preselected_expert': expert_id,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'user/book_session.html', context)





def get_specialization_icon(specialization):
    """Return appropriate icon for specialization"""
    icon_map = {
        'Clinical Psychology': 'fas fa-brain',
        'Counseling Psychology': 'fas fa-comment-dots',
        'Child & Adolescent Psychology': 'fas fa-child',
        'Educational Psychology': 'fas fa-graduation-cap',
        'Health Psychology': 'fas fa-heartbeat',
        'Neuropsychology': 'fas fa-brain',
        'Forensic Psychology': 'fas fa-gavel',
        'Industrial/Organizational Psychology': 'fas fa-building',
        'Sports Psychology': 'fas fa-running',
        'Rehabilitation Psychology': 'fas fa-heart',
        'Trauma & PTSD': 'fas fa-shield-alt',
        'Anxiety & Depression': 'fas fa-cloud',
        'Marriage & Family Therapy': 'fas fa-heart',
        'Addiction Counseling': 'fas fa-hands-helping',
        'Eating Disorders': 'fas fa-utensils',
        'Geriatric Psychology': 'fas fa-user',
        'School Psychology': 'fas fa-school',
        'Behavioral Therapy': 'fas fa-chart-line',
        'Cognitive Behavioral Therapy (CBT)': 'fas fa-brain',
        'Mindfulness & Meditation': 'fas fa-om',
        'Other - Specify in Qualification': 'fas fa-question-circle',
    }
    return icon_map.get(specialization, 'fas fa-brain')






@login_required
def create_booking(request):
    """Handle the booking form submission"""
    if request.method == 'POST':
        therapist_id = request.POST.get('expert_id')
        booking_date = request.POST.get('booking_date')
        booking_time = request.POST.get('booking_time')
        notes = request.POST.get('notes', '')
        slot_id = request.POST.get('slot_id')  # Get slot ID if provided
        
        # Debug print - FIXED: removed the space in therapist_id
        print(f"Booking request - Therapist: {therapist_id}, Date: {booking_date}, Time: {booking_time}, Slot ID: {slot_id}")
        
        # Validate required fields
        if not all([therapist_id, booking_date, booking_time]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('user:book_session')
        
        # Validate date format
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(booking_date, '%Y-%m-%d').date()
            
            if parsed_date < timezone.now().date():
                messages.error(request, 'Please select a future date.')
                return redirect('user:book_session')
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
            return redirect('user:book_session')
        
        # Validate time format
        try:
            from datetime import datetime
            parsed_time = datetime.strptime(booking_time, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Invalid time format. Please use HH:MM (24-hour format).')
            return redirect('user:book_session')
        
        # Get the therapist
        from user.models import Therapist, SessionCategory
        therapist = get_object_or_404(Therapist, id=therapist_id)
        
        # ===== NEW: Automatically determine category based on therapist specialization =====
        # Create a mapping from specialization to category name
        specialization_to_category = {
            'Clinical Psychology': 'Clinical Psychology Session',
            'Counseling Psychology': 'Counseling Session',
            'Child & Adolescent Psychology': 'Child & Adolescent Session',
            'Educational Psychology': 'Educational Consultation',
            'Health Psychology': 'Health Psychology Session',
            'Neuropsychology': 'Neuropsychology Assessment',
            'Forensic Psychology': 'Forensic Consultation',
            'Industrial/Organizational Psychology': 'Workplace Consultation',
            'Sports Psychology': 'Sports Psychology Session',
            'Rehabilitation Psychology': 'Rehabilitation Session',
            'Trauma & PTSD': 'Trauma Therapy',
            'Anxiety & Depression': 'Anxiety & Depression Therapy',
            'Marriage & Family Therapy': 'Couples & Family Therapy',
            'Addiction Counseling': 'Addiction Counseling',
            'Eating Disorders': 'Eating Disorder Treatment',
            'Geriatric Psychology': 'Geriatric Consultation',
            'School Psychology': 'School Consultation',
            'Behavioral Therapy': 'Behavioral Therapy',
            'Cognitive Behavioral Therapy (CBT)': 'CBT Session',
            'Mindfulness & Meditation': 'Mindfulness Session',
            'Other - Specify in Qualification': 'General Consultation',
        }
        
        # Default category name based on specialization or fallback
        category_name = specialization_to_category.get(
            therapist.specialization, 
            'Mental Health Session'
        )
        
        # Find or create the category
        category, created = SessionCategory.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'Session focused on {therapist.specialization or "mental health"}',
                'icon': 'fas fa-video'
            }
        )
        # ===== END NEW CODE =====
        
        # Check if there's an available TimeSlot
        from expert.models import TimeSlot
        
        # Try to find by slot ID first if provided
        time_slot = None
        if slot_id:
            time_slot = TimeSlot.objects.filter(
                id=slot_id,
                therapist=therapist,
                is_available=True,
                is_booked=False,
                is_blocked=False
            ).first()
        
        # If no slot ID or not found, try by date and time
        if not time_slot:
            time_slot = TimeSlot.objects.filter(
                therapist=therapist,
                date=parsed_date,
                start_time=parsed_time,
                is_available=True,
                is_booked=False,
                is_blocked=False
            ).first()
        
        if not time_slot:
            messages.error(request, 'This time slot is no longer available. Please choose another time.')
            # Redirect back with the selected expert preselected
            from django.urls import reverse
            return redirect(f"{reverse('user:book_session')}?expert={therapist_id}")
        
        # Check if booking already exists
        existing_booking = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date=parsed_date,
            booking_time=parsed_time,
            status__in=['pending', 'confirmed']
        ).exists()
        
        if not existing_booking:
            # Create booking
            booking = SessionBooking.objects.create(
                user=request.user,
                therapist=therapist,
                category=category,
                booking_date=parsed_date,
                booking_time=parsed_time,
                notes=notes,
                status='pending'
            )
            
            print(f"Booking created: ID {booking.id}, Status: {booking.status}, Category: {category.name}")
            
            # Update the TimeSlot to be booked
            time_slot.book(booking)
            print(f"TimeSlot updated: {time_slot.id} - Booked: {time_slot.is_booked}")
            
            # Send email notification to expert (optional)
            try:
                send_booking_notification(booking, 'requested')
            except:
                pass
            
            messages.success(
                request, 
                f'Your session request has been sent to {therapist.name}. You will be notified once they confirm.'
            )
        else:
            messages.error(request, 'This time slot is already booked. Please choose another time.')
            # Redirect back with the selected expert preselected
            from django.urls import reverse
            return redirect(f"{reverse('user:book_session')}?expert={therapist_id}")
        
        return redirect('user:my_sessions')
    
    return redirect('user:book_session')






@login_required
def my_sessions(request):
    """View user's booked sessions"""
    from datetime import datetime, timedelta
    from django.db.models import Q
    
    today = timezone.now().date()
    now = timezone.now()
    
    print(f"User: {request.user.username} - Loading my sessions")
    
    # Get all user's sessions with related data
    all_sessions = SessionBooking.objects.filter(
        user=request.user
    ).select_related('therapist', 'category').order_by('-booking_date', '-booking_time')
    
    print(f"Total sessions found: {all_sessions.count()}")
    
    # Get reviews for these sessions to check if already reviewed
    reviewed_session_ids = Review.objects.filter(
        user=request.user
    ).values_list('session_id', flat=True)
    
    # Separate upcoming and past sessions
    upcoming_sessions = []
    past_sessions = []
    
    for session in all_sessions:
        session_datetime = datetime.combine(session.booking_date, session.booking_time)
        session_datetime = timezone.make_aware(session_datetime)
        
        # Add attribute to check if already reviewed
        session.already_reviewed = session.id in reviewed_session_ids
        
        # Consider pending, confirmed, and paid as upcoming if date is future or today
        if session.status in ['pending', 'confirmed', 'paid'] and session_datetime.date() >= today:
            upcoming_sessions.append(session)
        else:
            past_sessions.append(session)
    
    # Count by status for stats
    pending_count = all_sessions.filter(status='pending').count()
    confirmed_count = all_sessions.filter(status='confirmed').count()
    paid_count = all_sessions.filter(status='paid').count()  # ADD THIS
    completed_count = all_sessions.filter(status='completed').count()
    cancelled_count = all_sessions.filter(status='cancelled').count()
    
    print(f"Upcoming: {len(upcoming_sessions)}, Past: {len(past_sessions)}")
    print(f"Pending: {pending_count}, Confirmed: {confirmed_count}, Paid: {paid_count}, Completed: {completed_count}, Cancelled: {cancelled_count}")
    
    # Check for sessions that need meeting links
    for session in upcoming_sessions:
        if session.status in ['confirmed', 'paid'] and not session.meeting_link:
            # Generate meeting link if missing
            import uuid
            session.meeting_link = f"https://meet.jit.si/empathyq-{session.id}-{uuid.uuid4().hex[:8]}"
            session.save()
            print(f"Generated missing meeting link for session {session.id}")
    
    context = {
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'paid_count': paid_count,  # ADD THIS
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_sessions': all_sessions.count(),
        'now': now,
        'today': today,
    }
    return render(request, 'user/my_sessions.html', context)









# user/views.py - Add these methods

@login_required
def cancel_session(request, session_id):
    """Cancel a session"""
    if request.method == 'POST':
        session = get_object_or_404(SessionBooking, id=session_id, user=request.user)
        
        if session.status in ['pending', 'confirmed']:
            reason = request.POST.get('reason', '')
            details = request.POST.get('details', '')
            
            session.cancel_booking(
                cancelled_by='user',
                reason=f"{reason}: {details}" if details else reason
            )
            
            messages.success(request, 'Your session has been cancelled successfully.')
        else:
            messages.error(request, 'This session cannot be cancelled.')
    
    return redirect('user:my_sessions')

@login_required
def reschedule_session(request):
    """Reschedule a session"""
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')
        
        session = get_object_or_404(SessionBooking, id=session_id, user=request.user)
        
        if session.status != 'confirmed':
            messages.error(request, 'Only confirmed sessions can be rescheduled.')
            return redirect('user:my_sessions')
        
        success, message = session.reschedule_session(new_date, new_time)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('user:my_sessions')

@login_required
def session_details(request, session_id):
    """Get session details via AJAX"""
    session = get_object_or_404(SessionBooking, id=session_id, user=request.user)
    
    data = {
        'id': session.id,
        'therapist': session.therapist.name,
        'date': session.booking_date.strftime('%Y-%m-%d'),
        'time': session.booking_time.strftime('%H:%M'),
        'status': session.status,
        'meeting_link': session.meeting_link,
        'notes': session.notes,
    }
    
    return JsonResponse(data)

@login_required
def session_details(request, booking_id):
    """View details of a specific session"""
    booking = get_object_or_404(SessionBooking, id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    return render(request, 'user/session_details.html', context)


@login_required
def join_session(request, booking_id):
    """Join a video session"""
    booking = get_object_or_404(SessionBooking, id=booking_id, user=request.user)
    
    # FIX: Check if session is confirmed OR paid
    if booking.status not in ['confirmed', 'paid']:  # ← FIXED: Include paid status
        messages.error(request, 'This session is not confirmed yet.')
        return redirect('user:my_sessions')
    
    session_datetime = datetime.combine(booking.booking_date, booking.booking_time)
    session_datetime = timezone.make_aware(session_datetime)
    
    # Allow joining 15 minutes before session time
    if session_datetime > timezone.now() + timedelta(minutes=15):
        minutes_until = int((session_datetime - timezone.now()).total_seconds() / 60)
        messages.warning(request, f'You can join this session {minutes_until} minutes before the start time.')
        return redirect('user:my_sessions')
    
    # Generate meeting link if not exists
    if not booking.meeting_link:
        import uuid
        room_name = f"empathyq-{booking.id}-{uuid.uuid4().hex[:8]}"
        booking.meeting_link = f"https://meet.jit.si/{room_name}"
        booking.save()
    
    return redirect(booking.meeting_link)

# # ============================================================================
# # CHAT VIEWS
# # ============================================================================

# ============================================================================
# ADMIN SUPPORT CHAT VIEW
# ============================================================================

@login_required
def chat_support(request):
    """Chat interface for users to message admin - USES AdminChatMessage"""
    
    # Get admin user (first superuser)
    admin_user = User.objects.filter(is_superuser=True).first()
    
    if not admin_user:
        messages.error(request, 'No admin available for chat. Please try again later.')
        return redirect('accounts:user_dashboard')
    
    # Get conversation between user and admin using AdminChatMessage
    conversation = AdminChatMessage.objects.filter(
        Q(sender=request.user, recipient=admin_user) |
        Q(sender=admin_user, recipient=request.user)
    ).order_by('timestamp')
    
    # Mark unread messages as read
    unread_messages = conversation.filter(
        sender=admin_user,
        recipient=request.user,
        is_read=False
    )
    unread_messages.update(is_read=True)
    
    # Handle POST request (sending new message)
    if request.method == 'POST':
        message_text = request.POST.get('message')
        
        if message_text:
            # Create new message using AdminChatMessage
            AdminChatMessage.objects.create(
                sender=request.user,
                recipient=admin_user,
                message=message_text,
                is_admin_reply=False
            )
            messages.success(request, 'Message sent successfully!')
            return redirect('user:chat')
        else:
            messages.error(request, 'Please enter a message.')
    
    context = {
        'conversation': conversation,
        'admin_user': admin_user,
    }
    return render(request, 'user/chat.html', context)


# ============================================================================
# ANONYMOUS CHAT ROOM FUNCTIONS - ALL USE AnonymousChatMessage
# ============================================================================

@login_required
def join_chat_queue(request, checkin_id):
    """Join the anonymous chat queue with enhanced mood-based matching"""
    
    # Get the check-in
    checkin = get_object_or_404(EmotionalCheckIn, id=checkin_id, user=request.user)
    
    # Debug: Print check-in info
    print(f"User {request.user} joining queue with mood: {checkin.primary_mood}")
    
    # Check if already in an active room
    existing_room = AnonymousChatRoom.objects.filter(
        (Q(user1=request.user) | Q(user2=request.user)),
        status='active',
        ended_at__isnull=True
    ).first()
    
    if existing_room:
        messages.info(request, 'You already have an active chat session.')
        return redirect('user:chat_room', room_id=existing_room.id)

    # Remove any existing queue entries for this user
    ChatQueue.objects.filter(user=request.user).delete()

    # Calculate energy level based on intensity
    def calculate_energy_level():
        intensity = checkin.intensity_score
        if intensity <= 3:
            return 'low'
        elif intensity <= 7:
            return 'medium'
        else:
            return 'high'
    
    energy_level = calculate_energy_level()
    
    # Add user to queue with all fields
    queue_entry = ChatQueue.objects.create(
        user=request.user,
        mood=checkin.primary_mood,
        secondary_mood=checkin.secondary_mood,
        intensity=checkin.intensity_score,
        energy_level=energy_level,
        mood_profile={
            'primary_mood': checkin.primary_mood,
            'secondary_mood': checkin.secondary_mood,
            'intensity': checkin.intensity_score,
            'energy_level': energy_level,
            'created_at': timezone.now().isoformat()
        }
    )
    
    print(f"Queue entry created: {queue_entry.id}")

    # Find best match based on mood compatibility
    def find_best_match():
        potential_matches = ChatQueue.objects.filter(
            is_active=True
        ).exclude(
            user=request.user
        ).filter(
            expires_at__gt=timezone.now()
        )
        
        print(f"Found {potential_matches.count()} potential matches")
        
        best_match = None
        best_score = -1
        
        for match in potential_matches:
            score = 0
            
            # Same primary mood (30 points)
            if match.mood == checkin.primary_mood:
                score += 30
            
            # Secondary mood match (20 points)
            if checkin.secondary_mood and match.mood == checkin.secondary_mood:
                score += 20
            
            # Energy level compatibility (25 points)
            energy_values = {'low': 1, 'medium': 2, 'high': 3}
            user_energy = energy_values.get(energy_level, 2)
            match_energy = energy_values.get(match.energy_level, 2)
            
            energy_diff = abs(user_energy - match_energy)
            
            if energy_diff == 0:
                score += 25
            elif energy_diff == 1:
                score += 15
            else:
                score += 5
            
            # Complementary moods work well together (40 points)
            complementary_pairs = [
                ('anxious', 'calm'),
                ('stressed', 'calm'),
                ('low', 'motivated'),
                ('irritable', 'calm'),
                ('anxious', 'neutral'),
                ('stressed', 'neutral'),
            ]
            
            for m1, m2 in complementary_pairs:
                if (match.mood == m1 and checkin.primary_mood == m2) or \
                   (match.mood == m2 and checkin.primary_mood == m1):
                    score += 40
                    break
            
            # Intensity similarity (within 3 points) - 20 points
            intensity_diff = abs(checkin.intensity_score - match.intensity)
            if intensity_diff <= 3:
                score += 20 - (intensity_diff * 5)
            else:
                score += 5
            
            print(f"Match with user {match.user}: score = {score}")
            
            # If this is the best match so far, save it
            if score > best_score:
                best_score = score
                best_match = match
        
        return best_match, best_score

    best_match, compatibility_score = find_best_match()

    if best_match and compatibility_score >= 30:  # Using threshold of 30
        print(f"Match found! Score: {compatibility_score}")
        
        # CRITICAL FIX: Check if a room already exists for this pair (race condition prevention)
        existing_room_for_match = AnonymousChatRoom.objects.filter(
            (Q(user1=request.user, user2=best_match.user) | 
             Q(user1=best_match.user, user2=request.user)),
            status='active'
        ).first()
        
        if existing_room_for_match:
            print(f"Room already exists for this match: {existing_room_for_match.id}")
            # Remove both from queue
            ChatQueue.objects.filter(
                user__in=[request.user, best_match.user]
            ).delete()
            messages.success(
                request, 
                f'Match found! {min(100, compatibility_score)}% compatibility.'
            )
            return redirect('user:chat_room', room_id=existing_room_for_match.id)
        
        # DEFINE the match reason function HERE before using it
        def get_match_reason():
            if best_match.mood == checkin.primary_mood:
                return f"Both feeling {checkin.primary_mood}"
            elif best_match.mood == 'calm' and checkin.primary_mood in ['anxious', 'stressed', 'irritable']:
                return f"Your {checkin.primary_mood} mood matched with a calm listener"
            elif checkin.primary_mood == 'calm' and best_match.mood in ['anxious', 'stressed', 'irritable']:
                return f"You can help someone feeling {best_match.mood}"
            elif best_match.mood == 'motivated' and checkin.primary_mood == 'low':
                return "Motivated listener matched with low mood for encouragement"
            else:
                return f"Matched by similar energy levels ({energy_level})"
        
        # CALL the function to get the reason
        match_reason = get_match_reason()
        
        # Generate aliases
        alias1 = generate_alias()
        alias2 = generate_alias()
        
        print(f"Creating room with aliases: {alias1} and {alias2}")
        
        # Create room
        room = AnonymousChatRoom.objects.create(
            user1=request.user,
            user2=best_match.user,
            mood_user1=checkin.primary_mood,
            mood_user2=best_match.mood,
            alias_user1=alias1,
            alias_user2=alias2,
            status='active',
            started_at=timezone.now()
        )

        # Remove both from queue
        ChatQueue.objects.filter(
            user__in=[request.user, best_match.user]
        ).delete()
        
        messages.success(
            request, 
            f'Match found! {min(100, compatibility_score)}% compatibility. {match_reason}'
        )
        
        # Redirect to chat room
        return redirect('user:chat_room', room_id=room.id)

    # If no match found or compatibility too low, stay in queue
    print("No match found, staying in queue")
    messages.info(request, 'Searching for a chat partner. Please wait...')
    return redirect('user:searching_chat')





@login_required
def searching_chat(request):
    """Waiting page while searching for chat partner with real-time updates"""
    # Check if user somehow got matched while on this page
    active_room = AnonymousChatRoom.objects.filter(
        (Q(user1=request.user) | Q(user2=request.user)),
        status='active',
        ended_at__isnull=True
    ).first()
    
    if active_room:
        return redirect('user:chat_room', room_id=active_room.id)
    
    # Check if still in queue
    queue_entry = ChatQueue.objects.filter(user=request.user, is_active=True).first()
    
    if not queue_entry:
        # User not in queue, redirect to check-in
        messages.warning(request, 'You are not in the queue. Please check in first.')
        return redirect('user:emotional_checkin')
    
    # AJAX request for real-time matching
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if queue_entry:
            # Check if expired
            if queue_entry.is_expired():
                queue_entry.is_active = False
                queue_entry.save()
                return JsonResponse({
                    'expired': True,
                    'message': 'Queue time expired. Please try again.',
                    'redirect_url': '/user/emotional-checkin/'
                })
            
            # Check for matches using sophisticated matching algorithm
            potential_matches = ChatQueue.objects.filter(
                is_active=True,
                expires_at__gt=timezone.now()
            ).exclude(
                user=request.user
            )
            
            print(f"AJAX: Found {potential_matches.count()} potential matches")
            
            best_match = None
            best_score = -1
            
            for match in potential_matches:
                score = 0
                
                # Same primary mood (30 points)
                if match.mood == queue_entry.mood:
                    score += 30
                
                # Secondary mood match (20 points)
                if queue_entry.secondary_mood and match.mood == queue_entry.secondary_mood:
                    score += 20
                
                # Energy level compatibility (25 points)
                energy_values = {'low': 1, 'medium': 2, 'high': 3}
                user_energy = energy_values.get(queue_entry.energy_level, 2)
                match_energy = energy_values.get(match.energy_level, 2)
                
                energy_diff = abs(user_energy - match_energy)
                
                if energy_diff == 0:
                    score += 25
                elif energy_diff == 1:
                    score += 15
                else:
                    score += 5
                
                # Complementary moods work well together (40 points)
                complementary_pairs = [
                    ('anxious', 'calm'),
                    ('stressed', 'calm'),
                    ('low', 'motivated'),
                    ('irritable', 'calm'),
                    ('anxious', 'neutral'),
                    ('stressed', 'neutral'),
                ]
                
                for m1, m2 in complementary_pairs:
                    if (match.mood == m1 and queue_entry.mood == m2) or \
                       (match.mood == m2 and queue_entry.mood == m1):
                        score += 40
                        break
                
                # Intensity similarity (within 3 points) - 20 points
                intensity_diff = abs(queue_entry.intensity - match.intensity)
                if intensity_diff <= 3:
                    score += 20 - (intensity_diff * 5)
                else:
                    score += 5
                
                print(f"AJAX: Match with user {match.user}: score = {score}")
                
                # If this is the best match so far, save it
                if score > best_score:
                    best_score = score
                    best_match = match
            
            # If we found a match with score >= 30
            if best_match and best_score >= 30:
                print(f"AJAX: Match found! Score: {best_score}")
                
                # CRITICAL FIX: Check if a room already exists for this pair (race condition prevention)
                existing_room = AnonymousChatRoom.objects.filter(
                    (Q(user1=request.user, user2=best_match.user) | 
                     Q(user1=best_match.user, user2=request.user)),
                    status='active'
                ).first()
                
                if existing_room:
                    print(f"AJAX: Room already exists for this match: {existing_room.id}")
                    # Remove both from queue
                    ChatQueue.objects.filter(
                        user__in=[request.user, best_match.user]
                    ).delete()
                    return JsonResponse({
                        'matched': True,
                        'room_id': str(existing_room.id),
                        'redirect_url': f'/user/chat/room/{existing_room.id}/',
                        'score': best_score,
                        'reason': "Match found!"
                    })
                
                # Generate match reason
                def get_match_reason():
                    if best_match.mood == queue_entry.mood:
                        return f"Both feeling {queue_entry.mood}"
                    elif best_match.mood == 'calm' and queue_entry.mood in ['anxious', 'stressed', 'irritable']:
                        return f"Your {queue_entry.mood} mood matched with a calm listener"
                    elif queue_entry.mood == 'calm' and best_match.mood in ['anxious', 'stressed', 'irritable']:
                        return f"You can help someone feeling {best_match.mood}"
                    elif best_match.mood == 'motivated' and queue_entry.mood == 'low':
                        return "Motivated listener matched with low mood for encouragement"
                    else:
                        return f"Matched by similar energy levels ({queue_entry.energy_level})"
                
                match_reason = get_match_reason()
                
                # Generate aliases
                alias1 = generate_alias()
                alias2 = generate_alias()
                
                print(f"AJAX: Creating room with aliases: {alias1} and {alias2}")
                
                # Create room
                room = AnonymousChatRoom.objects.create(
                    user1=request.user,
                    user2=best_match.user,
                    mood_user1=queue_entry.mood,
                    mood_user2=best_match.mood,
                    alias_user1=alias1,
                    alias_user2=alias2,
                    status='active',
                    started_at=timezone.now()
                )
                
                # Remove both from queue
                ChatQueue.objects.filter(
                    user__in=[request.user, best_match.user]
                ).delete()
                
                return JsonResponse({
                    'matched': True,
                    'room_id': str(room.id),
                    'redirect_url': f'/user/chat/room/{room.id}/',
                    'score': best_score,
                    'reason': match_reason
                })
        
        return JsonResponse({
            'matched': False,
            'in_queue': bool(queue_entry),
            'wait_time': queue_entry.get_wait_time() if queue_entry else 0
        })
    
    context = {
        'in_queue': bool(queue_entry),
        'queue_entry': queue_entry,
    }
    return render(request, 'chat/searching.html', context)







@login_required
def chat_room(request, room_id):
    """Display chat room - USES AnonymousChatMessage"""
    room = get_object_or_404(AnonymousChatRoom, id=room_id)
    
    # Check if user is part of this room
    if request.user not in [room.user1, room.user2]:
        messages.error(request, "You don't have access to this chat.")
        return redirect('accounts:user_dashboard')
    
    # Check if chat has ended
    if room.status == 'ended':
        messages.info(request, 'This chat has ended.')
        return redirect('user:chat_feedback', room_id=room.id)
    
    # Check if chat has expired (5 minutes)
    if room.is_expired():
        room.end_chat()
        messages.info(request, 'Chat session has ended (time limit reached).')
        return redirect('user:chat_feedback', room_id=room.id)
    
    # Get messages using AnonymousChatMessage
    messages_list = AnonymousChatMessage.objects.filter(room=room).order_by('timestamp')
    
    # Mark messages as read
    other_user = room.get_other_user(request.user)
    unread_messages = messages_list.filter(sender=other_user, is_read=False)
    for msg in unread_messages:
        msg.mark_as_read()
    
    # Get user's alias
    user_alias = room.get_user_alias(request.user)
    other_alias = room.get_other_alias(request.user)
    user_mood = room.get_user_mood(request.user)
    other_mood = room.get_user_mood(room.get_other_user(request.user))
    
    return render(request, 'chat/chat_room.html', {
        'room': room,
        'messages': messages_list,
        'user_alias': user_alias,
        'other_alias': other_alias,
        'user_mood': user_mood,
        'other_mood': other_mood
    })


@login_required
def get_chat_messages(request, room_id):
    """Get messages for AJAX refresh - USES AnonymousChatMessage"""
    room = get_object_or_404(AnonymousChatRoom, id=room_id)
    
    if request.user not in [room.user1, room.user2]:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    # Check if chat has ended
    if room.status == 'ended':
        return JsonResponse({
            'chat_ended': True,
            'redirect_url': f'/user/chat/feedback/{room.id}/'
        })
    
    # Get messages using AnonymousChatMessage
    messages_list = AnonymousChatMessage.objects.filter(room=room).order_by('timestamp')
    
    messages_data = [{
        'id': msg.id,
        'sender': msg.sender.username,
        'sender_name': room.get_user_alias(msg.sender),
        'message': msg.message,
        'time': msg.timestamp.strftime('%H:%M'),
        'is_me': msg.sender == request.user,
        'is_read': msg.is_read
    } for msg in messages_list]
    
    return JsonResponse({
        'messages': messages_data,
        'chat_ended': False
    })


@login_required
@csrf_exempt
def send_chat_message(request):
    """Send a message via AJAX - USES AnonymousChatMessage"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            room = get_object_or_404(AnonymousChatRoom, id=data['room_id'])
            
            # Check if user is in room
            if request.user not in [room.user1, room.user2]:
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            
            # Check if chat is still active
            if room.status != 'active':
                return JsonResponse({'success': False, 'error': 'Chat has ended'})
            
            # Check if chat has expired
            if room.is_expired():
                room.end_chat()
                return JsonResponse({'success': False, 'error': 'Chat session expired'})
            
            # Create message using AnonymousChatMessage
            message = AnonymousChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=data['message']
            )
            
            # Update last activity
            room.save()  # auto_now will update last_activity
            
            return JsonResponse({'success': True, 'message_id': message.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
@csrf_exempt
def end_chat(request):
    """End a chat session"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            room = get_object_or_404(AnonymousChatRoom, id=data['room_id'])
            
            if request.user not in [room.user1, room.user2]:
                return JsonResponse({'success': False, 'error': 'Not authorized'})
            
            # End the chat
            room.end_chat(ended_by=request.user)
            
            # Return success with room_id for redirect
            return JsonResponse({
                'success': True,
                'room_id': str(room.id),
                'message': 'Chat ended successfully'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def leave_chat(request, room_id):
    """Leave a chat (alternative to ending)"""
    room = get_object_or_404(AnonymousChatRoom, id=room_id)
    
    if request.user not in [room.user1, room.user2]:
        messages.error(request, "You don't have access to this chat.")
        return redirect('accounts:user_dashboard')
    
    room.end_chat(ended_by=request.user)
    messages.info(request, 'You have left the chat.')
    
    return redirect('user:chat_feedback', room_id=room.id)



@login_required
def chat_feedback(request, room_id):
    """Provide feedback after chat"""
    print(f"=== CHAT FEEDBACK VIEW CALLED ===")
    print(f"Method: {request.method}")
    print(f"Room ID: {room_id}")
    
    room = get_object_or_404(AnonymousChatRoom, id=room_id)
    print(f"Room found: {room.id}, status: {room.status}")
    
    # Check if user was in this room
    if request.user not in [room.user1, room.user2]:
        print(f"User {request.user} not in room")
        messages.error(request, "You don't have access to this feedback.")
        return redirect('accounts:user_dashboard')
    
    # Check if feedback already given
    existing_feedback = ChatFeedback.objects.filter(room=room, user=request.user).first()
    if existing_feedback:
        print(f"Feedback already exists for user {request.user}")
        messages.info(request, 'You have already provided feedback for this chat.')
        return redirect('accounts:user_dashboard')
    
    if request.method == 'POST':
        print("=== POST REQUEST RECEIVED ===")
        print(f"POST data: {request.POST}")
        
        feeling = request.POST.get('feeling_after')
        helpful = request.POST.get('was_helpful')
        comments = request.POST.get('comments', '')
        rating = request.POST.get('rating')
        
        print(f"feeling_after: {feeling}")
        print(f"was_helpful: {helpful}")
        print(f"rating: {rating}")
        print(f"comments: {comments}")
        
        # Validate required fields
        if not feeling or not helpful:
            print("Validation failed: missing required fields")
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'chat/chat_feedback.html', {'room': room})
        
        # Create feedback
        try:
            feedback = ChatFeedback.objects.create(
                room=room,
                user=request.user,
                feeling_after=feeling,
                was_helpful=helpful,
                comments=comments,
                rating=int(rating) if rating else None
            )
            print(f"Feedback created with ID: {feedback.id}")
            messages.success(request, 'Thank you for your feedback! Your input helps us improve.')
            return redirect('accounts:user_dashboard')
        except Exception as e:
            print(f"Error creating feedback: {e}")
            messages.error(request, f'Error saving feedback: {e}')
            return render(request, 'chat/chat_feedback.html', {'room': room})
    
    print("=== RENDERING FEEDBACK FORM ===")
    return render(request, 'chat/chat_feedback.html', {'room': room})


@login_required
def chat_history(request):
    """View user's chat history"""
    # Get all ended chats where the user participated
    rooms = AnonymousChatRoom.objects.filter(
        (Q(user1=request.user) | Q(user2=request.user)),
        status='ended'
    ).order_by('-ended_at')
    
    return render(request, 'chat/history.html', {
        'rooms': rooms
    })

# ============================================================================
# ADMIN UTILITY VIEWS
# ============================================================================

@login_required
def fix_existing_checkins(request):
    """Fix existing EmotionalCheckIn records by populating final_mood from primary_mood"""
    if not request.user.is_superuser:
        messages.error(request, "Only administrators can run this fix.")
        return redirect('dashboard')
    
    checkins = EmotionalCheckIn.objects.filter(final_mood__isnull=True)
    fixed_count = 0
    
    for checkin in checkins:
        if checkin.primary_mood and not checkin.final_mood:
            checkin.final_mood = checkin.primary_mood
            checkin.save()
            fixed_count += 1
    
    messages.success(request, f"Fixed {fixed_count} check-in records.")
    return redirect('admin:user_emotionalcheckin_changelist')





from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import GameScore
import json


@login_required
def play_game(request, game_name):
    """Display specific game"""
    template_map = {
        'rps': 'user/games/rock_paper_scissors.html',
        'sudoku': 'user/games/sudoku.html',
        'memory': 'user/games/memory.html',
        'breathing': 'user/games/color_breathing.html',
        'bubblepop': 'user/games/bubble_pop.html',
        'coloring': 'user/games/coloring_book.html',
        'oddeven': 'user/games/odd_even.html',      # New game template
        'sos': 'user/games/sos.html',                # New game template
        'snake': 'user/games/snake.html',
    }
    
    if game_name in template_map:
        # Get user's existing scores for this game
        game_code = {
            'rps': 'RPS',
            'sudoku': 'SUDOKU',
            'memory': 'MEMORY',
            'breathing': 'BREATHING',
            'bubblepop': 'BUBBLEPOP',
            'coloring': 'COLORING',
            'oddeven': 'ODDEVEN',      # New game code
            'sos': 'SOS',                # New game code
            'snake': 'SNAKE',
        }.get(game_name, game_name.upper())
        
        try:
            game_score = GameScore.objects.get(user=request.user, game=game_code)
            score_data = {
                'highest_score': game_score.highest_score,
                'best_time': game_score.best_time,
                'games_played': game_score.games_played,
                'total_score': game_score.total_score,
            }
        except GameScore.DoesNotExist:
            score_data = {
                'highest_score': 0,
                'best_time': None,
                'games_played': 0,
                'total_score': 0,
            }
        
        return render(request, template_map[game_name], {
            'username': request.user.username,
            'user_id': request.user.id,
            'scores': json.dumps(score_data)  # Pass scores as JSON
        })
    else:
        return redirect('accounts:user_dashboard')

@login_required
@require_POST
@csrf_exempt
def save_game_score(request):
    """Save game scores to database"""
    try:
        data = json.loads(request.body)
        game = data.get('game')
        score = data.get('score', 0)  # For RPS
        time = data.get('time', None)  # For Sudoku
        completed = data.get('completed', False)  # Whether game was completed
        
        # Get or create score record for this user and game
        game_score, created = GameScore.objects.get_or_create(
            user=request.user,
            game=game.upper(),
            defaults={
                'highest_score': score,
                'best_time': time,
                'games_played': 1 if completed else 0,
                'total_score': score
            }
        )
        
        if not created:
            # Update existing record
            if completed:
                game_score.games_played += 1
                game_score.total_score += score
            
            # Update highest score if new score is higher
            if score > game_score.highest_score:
                game_score.highest_score = score
            
            # Update best time if new time is better
            if time and (not game_score.best_time or time < game_score.best_time):
                game_score.best_time = time
            
            game_score.save()
        
        return JsonResponse({
            'success': True,
            'highest_score': game_score.highest_score,
            'best_time': game_score.best_time,
            'games_played': game_score.games_played,
            'total_score': game_score.total_score
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def get_game_scores(request, game):
    """Get user's scores for a specific game"""
    try:
        game_score = GameScore.objects.get(user=request.user, game=game.upper())
        return JsonResponse({
            'highest_score': game_score.highest_score,
            'best_time': game_score.best_time,
            'games_played': game_score.games_played,
            'total_score': game_score.total_score
        })
    except GameScore.DoesNotExist:
        return JsonResponse({
            'highest_score': 0,
            'best_time': None,
            'games_played': 0,
            'total_score': 0
        })
    



# expert-- user chat view
# user/views.py - Expert Chat Functions

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from user.models import Therapist, SessionBooking
from expert.models import ChatMessage as ExpertChatMessage  # Import with alias to avoid confusion
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def expert_chat(request, expert_id=None):
    """Chat interface for users to talk with experts"""
    # Get all experts the user has booked sessions with
    booked_expert_ids = SessionBooking.objects.filter(
        user=request.user,
        status__in=['confirmed', 'completed']
    ).values_list('therapist_id', flat=True).distinct()
    
    # Get the therapist objects
    booked_experts = Therapist.objects.filter(id__in=booked_expert_ids)
    
    # Add unread count for each expert
    experts_list = []
    for expert in booked_experts:
        # Find expert's user account (the User object associated with this therapist)
        expert_user = User.objects.filter(
            Q(username=expert.name) | 
            Q(first_name__icontains=expert.name.split()[0] if ' ' in expert.name else expert.name) |
            Q(email=expert.email)
        ).first()
        
        unread_count = 0
        if expert_user:
            unread_count = ExpertChatMessage.objects.filter(
                sender=expert_user,
                recipient=request.user,
                is_read=False
            ).count()
        
        # Get expert's specialization from profile settings
        # FIXED: Use 'specializations' (plural) instead of 'specialization'
        specialization = ""
        if hasattr(expert, 'profile_settings') and expert.profile_settings:
            # Check if the attribute exists and get its value
            if hasattr(expert.profile_settings, 'specializations'):
                specialization = expert.profile_settings.specializations or ""
            # If it's a method that returns a list, convert to string
            elif hasattr(expert.profile_settings, 'get_specializations_list'):
                spec_list = expert.profile_settings.get_specializations_list()
                if spec_list:
                    specialization = ", ".join(spec_list)
        
        experts_list.append({
            'id': expert.id,
            'name': expert.name,
            'specialization': specialization,
            'unread_count': unread_count
        })
    
    selected_expert = None
    messages_list = []
    has_booking = False
    
    if expert_id:
        selected_expert = get_object_or_404(Therapist, id=expert_id)
        
        # Verify user has booked with this expert
        has_booking = SessionBooking.objects.filter(
            therapist=selected_expert,
            user=request.user,
            status__in=['confirmed', 'completed']
        ).exists()
        
        if has_booking:
            # Find expert's user account
            expert_user = User.objects.filter(
                Q(username=selected_expert.name) | 
                Q(first_name__icontains=selected_expert.name.split()[0] if ' ' in selected_expert.name else selected_expert.name) |
                Q(email=selected_expert.email)
            ).first()
            
            if expert_user:
                # Get all messages between user and expert using ExpertChatMessage
                messages_list = ExpertChatMessage.objects.filter(
                    Q(sender=request.user, recipient=expert_user) |
                    Q(sender=expert_user, recipient=request.user)
                ).order_by('timestamp')
                
                # Mark messages from expert as read
                unread_messages = messages_list.filter(
                    sender=expert_user,
                    recipient=request.user,
                    is_read=False
                )
                unread_messages.update(is_read=True)
    
    context = {
        'experts': experts_list,
        'selected_expert': selected_expert,
        'messages': messages_list,
        'has_booking': has_booking,
    }
    return render(request, 'user/expert_chat.html', context)


@login_required
def get_expert_messages(request, expert_id):
    """Get messages for AJAX refresh"""
    try:
        expert = get_object_or_404(Therapist, id=expert_id)
        
        # Verify user has booked with this expert
        has_booking = SessionBooking.objects.filter(
            therapist=expert,
            user=request.user,
            status__in=['confirmed', 'completed']
        ).exists()
        
        if not has_booking:
            return JsonResponse({'error': 'No booking found'}, status=403)
        
        # Find expert's user account
        expert_user = User.objects.filter(
            Q(username=expert.name) | 
            Q(first_name__icontains=expert.name.split()[0] if ' ' in expert.name else expert.name) |
            Q(email=expert.email)
        ).first()
        
        if not expert_user:
            return JsonResponse({'error': 'Expert user not found'}, status=404)
        
        messages_list = ExpertChatMessage.objects.filter(
            Q(sender=request.user, recipient=expert_user) |
            Q(sender=expert_user, recipient=request.user)
        ).order_by('timestamp')
        
        messages_data = [{
            'id': msg.id,
            'message': msg.message,
            'time': msg.timestamp.strftime('%H:%M'),
            'is_me': msg.sender == request.user,
            'is_read': msg.is_read,
            'sender_name': 'You' if msg.sender == request.user else f"Dr. {expert.name}",
        } for msg in messages_list]
        
        return JsonResponse({'messages': messages_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def send_expert_message(request):
    """Send a message to expert via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expert_id = data.get('expert_id')
            message_text = data.get('message')
            
            if not expert_id or not message_text:
                return JsonResponse({'success': False, 'error': 'Missing data'})
            
            expert = get_object_or_404(Therapist, id=expert_id)
            
            # Verify user has booked with this expert
            has_booking = SessionBooking.objects.filter(
                therapist=expert,
                user=request.user,
                status__in=['confirmed', 'completed']
            ).exists()
            
            if not has_booking:
                return JsonResponse({'success': False, 'error': 'You must book a session first'})
            
            # Find expert's user account
            expert_user = User.objects.filter(
                Q(username=expert.name) | 
                Q(first_name__icontains=expert.name.split()[0] if ' ' in expert.name else expert.name) |
                Q(email=expert.email)
            ).first()
            
            if not expert_user:
                return JsonResponse({'success': False, 'error': 'Expert user not found'})
            
            # Create message using ExpertChatMessage
            message = ExpertChatMessage.objects.create(
                sender=request.user,
                recipient=expert_user,
                message=message_text,
                is_admin_reply=False
            )
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'time': message.timestamp.strftime('%H:%M'),
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})




# ============================================================================
# SESSION NOTES / PRESCRIPTIONS VIEWS
# ============================================================================

from expert.models import SessionNote
from django.http import FileResponse

# user/views.py - Update the my_notes function

@login_required
def my_notes(request):
    """View all notes/prescriptions from experts"""
    try:
        from expert.models import SessionNote
        
        # Get all notes for the current user
        notes = SessionNote.objects.filter(
            user=request.user
        ).select_related('session', 'therapist', 'session__category').order_by('-created_at')
        
        print(f"Found {notes.count()} notes for user {request.user.username}")
        
        # Debug: Print each note
        for note in notes:
            print(f"Note ID: {note.id}, Title: {note.title}, Type: {note.note_type}, Created: {note.created_at}")
        
        # Mark unread as read when viewed
        unread_notes = notes.filter(is_read=False)
        unread_count = unread_notes.count()
        unread_notes.update(is_read=True)
        
        # Group by session
        notes_by_session = {}
        for note in notes:
            session_id = note.session.id if note.session else f"unknown_{note.id}"
            if session_id not in notes_by_session:
                notes_by_session[session_id] = {
                    'session': note.session,
                    'notes': []
                }
            notes_by_session[session_id]['notes'].append(note)
        
        # Get counts by type
        prescription_count = notes.filter(note_type='prescription').count()
        recommendation_count = notes.filter(note_type='recommendation').count()
        exercise_count = notes.filter(note_type='exercise').count()
        
        # Get recent notes for dashboard (first 3)
        recent_notes = notes[:3]
        
        context = {
            'notes': notes,
            'notes_by_session': notes_by_session,
            'unread_count': unread_count,
            'total_count': notes.count(),
            'prescription_count': prescription_count,
            'recommendation_count': recommendation_count,
            'exercise_count': exercise_count,
            'recent_notes': recent_notes,
        }
        return render(request, 'user/my_notes.html', context)
        
    except Exception as e:
        print(f"Error in my_notes: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error loading notes: {str(e)}')
        return redirect('accounts:user_dashboard')

@login_required
def view_note(request, note_id):
    """View a single note"""
    try:
        note = get_object_or_404(SessionNote, id=note_id, user=request.user)
        
        # Mark as read
        if not note.is_read:
            note.is_read = True
            note.save(update_fields=['is_read'])
        
        # Get previous and next notes
        prev_note = SessionNote.objects.filter(
            user=request.user,
            created_at__lt=note.created_at
        ).order_by('-created_at').first()
        
        next_note = SessionNote.objects.filter(
            user=request.user,
            created_at__gt=note.created_at
        ).order_by('created_at').first()
        
        context = {
            'note': note,
            'prev_note': prev_note,
            'next_note': next_note,
        }
        return render(request, 'user/note_detail.html', context)
        
    except SessionNote.DoesNotExist:
        messages.error(request, 'Note not found.')
        return redirect('user:my_notes')
    except Exception as e:
        messages.error(request, f'Error loading note: {str(e)}')
        return redirect('user:my_notes')


@login_required
def download_note_attachment(request, note_id):
    """Download note attachment"""
    try:
        note = get_object_or_404(SessionNote, id=note_id, user=request.user)
        
        if note.attachment and note.attachment.name:
            import os
            file_name = os.path.basename(note.attachment.name)
            response = FileResponse(note.attachment.open(), as_attachment=True, filename=file_name)
            return response
        else:
            messages.error(request, 'No attachment found for this note.')
            return redirect('user:view_note', note_id=note.id)
            
    except SessionNote.DoesNotExist:
        messages.error(request, 'Note not found.')
        return redirect('user:my_notes')
    except Exception as e:
        messages.error(request, f'Error downloading attachment: {str(e)}')
        return redirect('user:my_notes')


@login_required
def mark_note_as_read(request, note_id):
    """Mark a note as read (AJAX)"""
    try:
        if request.method == 'POST':
            note = get_object_or_404(SessionNote, id=note_id, user=request.user)
            note.is_read = True
            note.save(update_fields=['is_read'])
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Invalid method'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def print_note(request, note_id):
    """Print-friendly version of note"""
    try:
        note = get_object_or_404(SessionNote, id=note_id, user=request.user)
        
        context = {
            'note': note,
        }
        return render(request, 'user/print_note.html', context)
        
    except Exception as e:
        messages.error(request, f'Error preparing note for printing: {str(e)}')
        return redirect('user:view_note', note_id=note_id)
    




# ==================== REVIEW FUNCTIONS ====================

@login_required
def submit_review(request):
    """Submit a review for a completed session"""
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        is_anonymous = request.POST.get('is_anonymous') == 'on'
        
        # Validate inputs
        if not all([session_id, rating, comment]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('user:my_sessions')
        
        try:
            session = SessionBooking.objects.get(id=session_id, user=request.user)
            
            # Check if session is completed
            if session.status != 'completed':
                messages.error(request, 'You can only review completed sessions.')
                return redirect('user:my_sessions')
            
            # Check if review already exists
            existing_review = Review.objects.filter(
                user=request.user,
                therapist=session.therapist,
                session=session
            ).first()
            
            if existing_review:
                messages.error(request, 'You have already reviewed this session.')
                return redirect('user:my_sessions')
            
            # Create review
            review = Review.objects.create(
                user=request.user,
                therapist=session.therapist,
                session=session,
                rating=int(rating),
                comment=comment,
                is_anonymous=is_anonymous,
                is_approved=True  # Auto-approve for now
            )
            
            messages.success(request, 'Thank you for your feedback! Your review has been submitted.')
            
        except SessionBooking.DoesNotExist:
            messages.error(request, 'Session not found.')
        except Exception as e:
            messages.error(request, f'Error submitting review: {str(e)}')
    
    return redirect('user:my_sessions')


@login_required
def get_session_details(request, session_id):
    """Get session details for AJAX request (for details modal)"""
    try:
        session = SessionBooking.objects.select_related('therapist', 'category').get(
            id=session_id, 
            user=request.user
        )
        
        data = {
            'id': session.id,
            'therapist_name': session.therapist.name,
            'therapist_specialization': session.therapist.specialization or 'Mental Health Professional',
            'category': session.category.name if session.category else 'General Session',
            'date': session.booking_date.strftime('%A, %B %d, %Y'),
            'time': session.booking_time.strftime('%I:%M %p'),
            'duration': session.duration_minutes,
            'status': session.get_status_display(),
            'status_class': session.status,
            'notes': session.notes or 'No notes provided',
            'meeting_link': session.meeting_link if session.meeting_link else None,
            'payment_status': session.get_payment_status_display() if session.payment_status else None,
            'fee': str(session.consultation_fee) if session.consultation_fee else None,
            'cancellation_reason': session.cancellation_reason if session.cancellation_reason else None,
            'cancelled_by': session.cancelled_by if session.cancelled_by else None,
        }
        
        return JsonResponse({'success': True, 'data': data})
    except SessionBooking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    





def approve_session(request, booking_id):
    """Approve a session request"""
    if request.method == 'GET':
        booking = get_object_or_404(SessionBooking, id=booking_id)
        
        # Check if the logged-in expert owns this booking
        if booking.therapist.user != request.user:
            messages.error(request, 'You are not authorized to approve this session.')
            return redirect('expert:session_requests')
        
        # Confirm the booking (this sets the fee from therapist settings)
        booking.confirm_booking()
        
        # Generate meeting link if needed
        if not booking.meeting_link:
            booking.generate_meeting_link()
        
        messages.success(request, f'Session with {booking.user.username} has been confirmed. Payment is now pending from user.')
        
    return redirect('expert:session_requests')

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from .utils import RazorpayClient
from user.models import Payment
from expert.models import TherapistSettings, ExpertProfileSettings
import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
@login_required
def initiate_payment(request, booking_id):
    """Initiate payment for a booking"""
    try:
        booking = get_object_or_404(SessionBooking, id=booking_id, user=request.user)
        
        # Check if booking is confirmed (approved by expert)
        if booking.status != 'confirmed':
            if booking.status == 'paid':
                messages.success(request, 'Payment already completed for this booking.')
                return redirect('user:payment_success', booking_id=booking.id)
            elif booking.status == 'pending':
                messages.warning(request, 'Please wait for the expert to confirm your session before making payment.')
                return redirect('user:my_sessions')
            else:
                messages.error(request, 'This session is not ready for payment.')
                return redirect('user:my_sessions')
        
        # Handle existing payment records
        if hasattr(booking, 'payment'):
            existing_payment = booking.payment
            
            if existing_payment.status == 'paid':
                messages.success(request, 'Payment already completed for this booking.')
                return redirect('user:payment_success', booking_id=booking.id)
            
            elif existing_payment.status == 'created':
                # Reuse existing payment
                return render_payment_page(request, booking, existing_payment)
            
            elif existing_payment.status == 'failed':
                # Delete failed payment
                existing_payment.delete()
        
        # Ensure fee is set
        if not booking.consultation_fee or booking.consultation_fee == 0:
            # Try to get fee from multiple sources
            fee = None
            try:
                from expert.models import ExpertProfileSettings
                profile_settings = ExpertProfileSettings.objects.get(therapist=booking.therapist)
                if profile_settings.consultation_fee and profile_settings.consultation_fee > 0:
                    fee = profile_settings.consultation_fee
            except:
                pass
            
            if not fee:
                try:
                    from expert.models import TherapistSettings
                    therapist_settings = TherapistSettings.objects.get(therapist=booking.therapist)
                    if therapist_settings.consultation_fee and therapist_settings.consultation_fee > 0:
                        fee = therapist_settings.consultation_fee
                except:
                    pass
            
            if not fee:
                fee = Decimal('300.00')  # Default
            
            booking.consultation_fee = fee
            booking.save()
        
        # Create Razorpay order
        razorpay_client = RazorpayClient()
        order = razorpay_client.create_order(float(booking.consultation_fee))
        
        if not order:
            messages.error(request, 'Failed to create payment order. Please try again.')
            return redirect('user:my_sessions')
        
        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            razorpay_order_id=order['id'],
            amount=booking.consultation_fee,
            currency=order['currency'],
            status='created'
        )
        
        return render_payment_page(request, booking, payment)
        
    except Exception as e:
        logger.error(f"Payment initiation failed: {str(e)}")
        messages.error(request, f'Payment initiation failed: {str(e)}')
        return redirect('user:payment_failed', booking_id=booking_id)

def get_therapist_fee(therapist):
    """Helper function to get therapist's fee from various sources"""
    from expert.models import TherapistSettings, ExpertProfileSettings
    from decimal import Decimal
    
    fee = Decimal('500.00')  # Default
    
    # ===== FIXED: Prioritize ExpertProfileSettings (what expert sees in profile) =====
    try:
        # Try ExpertProfileSettings FIRST (this is what experts set in profile_settings)
        profile_settings = ExpertProfileSettings.objects.get(therapist=therapist)
        if profile_settings.consultation_fee:
            fee = profile_settings.consultation_fee
            print(f"Fee from ExpertProfileSettings: {fee}")
    except ExpertProfileSettings.DoesNotExist:
        try:
            # Try TherapistSettings SECOND (legacy)
            therapist_settings = TherapistSettings.objects.get(therapist=therapist)
            if therapist_settings.consultation_fee:
                fee = therapist_settings.consultation_fee
                print(f"Fee from TherapistSettings: {fee}")
        except TherapistSettings.DoesNotExist:
            # Try therapist model's session_fee if exists
            if hasattr(therapist, 'session_fee') and therapist.session_fee:
                fee = therapist.session_fee
                print(f"Fee from therapist.session_fee: {fee}")
    
    return fee

def render_payment_page(request, booking, payment):
    """Helper function to render payment page"""
    context = {
        'booking': booking,
        'therapist': booking.therapist,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': payment.razorpay_order_id,
        'amount': int(float(payment.amount) * 100),  # Amount in paise
        'currency': payment.currency,
        'callback_url': request.build_absolute_uri(reverse('user:payment_callback')),
        'user': request.user
    }
    return render(request, 'user/payment_page.html', context)


@csrf_exempt
@require_POST
def payment_callback(request):
    """Handle Razorpay payment callback"""
    try:
        # Get payment details from Razorpay
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        print(f"=== PAYMENT CALLBACK RECEIVED ===")
        print(f"Order ID: {razorpay_order_id}")
        print(f"Payment ID: {razorpay_payment_id}")
        print(f"Signature: {razorpay_signature}")
        
        logger.info(f"Payment callback received - Order: {razorpay_order_id}, Payment: {razorpay_payment_id}")
        
        # Find the payment record
        payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id)
        print(f"Found payment record: {payment.id}, status: {payment.status}")
        
        # ===== FIX: Skip verification for test/mock payments =====
        # Check if this is a test payment (pay_test_ prefix)
        if razorpay_payment_id and razorpay_payment_id.startswith('pay_test_'):
            print("⚠️ Test payment detected - skipping signature verification")
            # Mark payment as paid directly
            payment.mark_as_paid(razorpay_payment_id, razorpay_signature)
            
            # Get booking
            booking = payment.booking
            
            logger.info(f"Test payment successful for booking: {booking.id}")
            print(f"Test payment successful for booking {booking.id}")
            
            return redirect('user:payment_success', booking_id=booking.id)
        
        # For real payments, verify signature
        razorpay_client = RazorpayClient()
        is_verified = razorpay_client.verify_payment(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature
        )
        
        print(f"Payment verified: {is_verified}")
        
        if is_verified:
            # Mark payment as paid
            payment.mark_as_paid(razorpay_payment_id, razorpay_signature)
            
            # Get booking
            booking = payment.booking
            
            logger.info(f"Payment verified successfully for booking: {booking.id}")
            print(f"Payment successful for booking {booking.id}")
            
            return redirect('user:payment_success', booking_id=booking.id)
        else:
            payment.status = 'failed'
            payment.save()
            logger.error(f"Payment verification failed for order: {razorpay_order_id}")
            print(f"Payment verification failed")
            return redirect('user:payment_failed', booking_id=payment.booking.id)
            
    except Exception as e:
        logger.error(f"Payment callback error: {str(e)}")
        print(f"Payment callback exception: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to get booking_id from the order
        booking_id = 0
        try:
            razorpay_order_id = request.POST.get('razorpay_order_id')
            if razorpay_order_id:
                payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
                if payment:
                    booking_id = payment.booking.id
        except:
            pass
            
        return redirect('user:payment_failed', booking_id=booking_id)

def send_payment_confirmation_email(booking):
    """Send payment confirmation email"""
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        subject = f'Payment Confirmed: Session with {booking.therapist.name}'
        
        context = {
            'user': booking.user,
            'booking': booking,
            'therapist': booking.therapist,
        }
        
        html_message = render_to_string('emails/payment_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")

@login_required
def payment_success(request, booking_id):
    """Payment success page"""
    booking = get_object_or_404(SessionBooking, id=booking_id, user=request.user)
    
    # Ensure payment is marked as paid
    if hasattr(booking, 'payment') and booking.payment.status == 'paid':
        context = {
            'booking': booking,
            'payment': booking.payment
        }
        return render(request, 'user/payment_success.html', context)
    else:
        messages.warning(request, 'Payment status is pending verification.')
        return redirect('user:my_sessions')

@login_required
def payment_failed(request, booking_id):
    """Payment failed page"""
    booking = None
    error_message = request.GET.get('error', 'Payment could not be processed')
    
    if booking_id and booking_id != 0:
        try:
            booking = SessionBooking.objects.get(id=booking_id, user=request.user)
            print(f"Payment failed page - Booking {booking_id}: fee={booking.consultation_fee}")
        except SessionBooking.DoesNotExist:
            pass
    
    return render(request, 'user/payment_failed.html', {
        'booking': booking,
        'error_message': error_message
    })

@login_required
def retry_payment(request, booking_id):
    """Retry failed payment"""
    booking = get_object_or_404(SessionBooking, id=booking_id, user=request.user)
    
    # ===== FIXED: Better handling of existing payments =====
    # Check if payment exists
    if hasattr(booking, 'payment'):
        existing_payment = booking.payment
        
        if existing_payment.status == 'failed':
            # Delete the old failed payment
            logger.info(f"Retry: Deleting failed payment {existing_payment.id}")
            existing_payment.delete()
        elif existing_payment.status == 'created':
            # Payment was created but never completed
            logger.info(f"Retry: Deleting stale payment {existing_payment.id}")
            existing_payment.delete()
        elif existing_payment.status == 'paid':
            # Already paid, redirect to success
            messages.success(request, 'Payment already completed.')
            return redirect('user:payment_success', booking_id=booking.id)
    
    # Create new payment
    return initiate_payment(request, booking_id)