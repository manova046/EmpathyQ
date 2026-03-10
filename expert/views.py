

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
import json
import uuid
from user.models import Review 
from datetime import datetime, timedelta, date
from user.models import SessionBooking, Therapist
from datetime import datetime  

# Fix these imports to match your models
from .models import (
    ExpertProfileSettings,
    Review,
    Availability,
    TimeSlot,  # Changed from GeneratedSlot to TimeSlot
    TimeOff,
    Booking,
    TherapistSettings  # Changed from TherapistProfile to TherapistSettings
)
# ==================== SESSION REQUEST FUNCTIONS ====================

@login_required
def session_requests(request):
    """View session requests for the logged-in therapist"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        
        print(f"Expert: {therapist.name} - Loading session requests")
        
        # Get all bookings for this therapist
        all_bookings = SessionBooking.objects.filter(
            therapist=therapist
        ).select_related('user', 'category').order_by('-booking_date', '-booking_time')
        
        print(f"Total bookings found: {all_bookings.count()}")
        
        # Separate into categories for better organization
        pending_requests = all_bookings.filter(status='pending')
        upcoming_sessions = all_bookings.filter(
            status='confirmed',
            booking_date__gte=timezone.now().date()
        )
        past_sessions = all_bookings.filter(
            status__in=['completed', 'cancelled', 'no_show']
        )[:20]  # Limit to last 20
        
        print(f"Pending: {pending_requests.count()}, Upcoming: {upcoming_sessions.count()}, Past: {past_sessions.count()}")
        
        # Debug: Print all pending bookings
        for booking in pending_requests:
            print(f"  Pending: {booking.id} - {booking.user.username} - {booking.booking_date} {booking.booking_time}")
        
    except Therapist.DoesNotExist:
        pending_requests = []
        upcoming_sessions = []
        past_sessions = []
        messages.warning(request, 'Therapist profile not found.')
        print("Therapist not found!")
    
    context = {
        'pending_requests': pending_requests,
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
    }
    return render(request, 'expert/session_requests.html', context)


# expert/views.py - Update approve_session function

@login_required
def approve_session(request, booking_id):
    """Approve a session booking and generate meeting link"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist, status='pending')
        
        # Update booking status
        booking.status = 'confirmed'
        booking.confirmed_at = timezone.now()
        
        # Generate meeting link (automatically done by model's save method)
        # The model's save method will call generate_meeting_link()
        booking.save()  # This will trigger meeting link generation
        
        # Update the corresponding TimeSlot
        from expert.models import TimeSlot
        time_slot = TimeSlot.objects.filter(
            therapist=therapist,
            date=booking.booking_date,
            start_time=booking.booking_time
        ).first()
        
        if time_slot:
            time_slot.book(booking)
            # Also update the TimeSlot's booking reference if needed
            time_slot.booking = booking
            time_slot.save()
        
        # Send notification to user (optional)
        try:
            # send_booking_notification(booking, 'approved')
            pass
        except:
            pass
        
        client_name = booking.user.get_full_name() or booking.user.username
        messages.success(
            request, 
            f'Session with {client_name} has been approved. A meeting link has been generated: {booking.meeting_link}'
        )
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except SessionBooking.DoesNotExist:
        messages.error(request, 'Booking not found or already processed.')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('expert:session_requests')

@login_required
def reject_session(request, booking_id):
    """Reject a session booking"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist, status='pending')
        
        # Store client name for message
        client_name = booking.user.get_full_name() or booking.user.username
        
        # Update booking status
        booking.status = 'cancelled'
        booking.cancelled_at = timezone.now()
        booking.save()
        
        # Release the corresponding TimeSlot
        from expert.models import TimeSlot
        time_slot = TimeSlot.objects.filter(
            therapist=therapist,
            date=booking.booking_date,
            start_time=booking.booking_time
        ).first()
        
        if time_slot:
            time_slot.release()
            # Clear the booking reference
            time_slot.booking = None
            time_slot.save()
        
        # Send notification to user (optional)
        try:
            # from .utils import send_booking_notification
            # send_booking_notification(booking, 'rejected')
            pass
        except:
            pass
        
        messages.success(request, f'Session request from {client_name} has been rejected. The time slot is now available again.')
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except SessionBooking.DoesNotExist:
        messages.error(request, 'Booking not found or already processed.')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('expert:session_requests')


# expert/views.py - Update the complete_session view

# expert/views.py - Update the complete_session view

# expert/views.py - Update the complete_session view

@login_required
def complete_session(request, booking_id):
    """Mark a session as completed with option to add notes/prescriptions"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist, status='confirmed')
        
        # Check if session is already completed
        if booking.status == 'completed':
            messages.info(request, 'This session is already marked as completed.')
            return redirect('expert:session_requests')
        
        # Store client name for message
        client_name = booking.user.get_full_name() or booking.user.username
        
        # If this is a POST request with note data
        if request.method == 'POST' and 'add_note' in request.POST:
            from .models import SessionNote
            
            # Debug print
            print(f"Creating session note for booking {booking.id}")
            print(f"POST data: {request.POST}")
            
            # Get note type from form
            note_type = request.POST.get('note_type', 'general')
            
            # Set title and content based on note type
            if note_type == 'general':
                title = request.POST.get('general_title', f'Post-Session Notes - {booking.booking_date}')
                content = request.POST.get('general_content', '')
            elif note_type == 'prescription':
                title = request.POST.get('prescription_title', f'Prescription - {booking.booking_date}')
                content = request.POST.get('prescription_content', '')
            elif note_type == 'exercise':
                title = request.POST.get('exercise_title', f'Exercise - {booking.booking_date}')
                content = request.POST.get('exercise_content', '')
            elif note_type == 'referral':
                title = request.POST.get('referral_title', f'Referral - {booking.booking_date}')
                content = request.POST.get('referral_content', '')
            else:
                title = request.POST.get('title', f'Post-Session Notes - {booking.booking_date}')
                content = request.POST.get('content', '')
            
            # Create session note
            note = SessionNote.objects.create(
                session=booking,
                therapist=therapist,
                user=booking.user,
                note_type=note_type,
                title=title,
                content=content,
                medication_name=request.POST.get('medication_name', ''),
                dosage=request.POST.get('dosage', ''),
                frequency=request.POST.get('frequency', ''),
                duration=request.POST.get('duration', ''),
                exercise_name=request.POST.get('exercise_name', ''),
                exercise_instructions=request.POST.get('exercise_instructions', ''),
                exercise_duration=request.POST.get('exercise_duration', ''),
                is_important=request.POST.get('is_important') == 'on',
            )
            
            # Handle file attachment
            if 'attachment' in request.FILES:
                note.attachment = request.FILES['attachment']
                note.save()
                print(f"Attachment saved: {note.attachment.name}")
            
            print(f"SessionNote created with ID: {note.id}, Title: {note.title}")
            messages.success(request, f'Notes added for {client_name}')
            
            # Continue with session completion
            return complete_session_process(request, therapist, booking, client_name, with_note=True)
        
        # If just completing without notes (simple POST)
        elif request.method == 'POST' and 'complete_only' in request.POST:
            return complete_session_process(request, therapist, booking, client_name)
        
        # Show the note form
        else:
            # Get existing notes if any
            from .models import SessionNote
            existing_note = SessionNote.objects.filter(session=booking).first()
            
            context = {
                'booking': booking,
                'therapist': therapist,
                'client_name': client_name,
                'existing_note': existing_note,
            }
            return render(request, 'expert/complete_session_form.html', context)
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('expert:session_requests')
    except SessionBooking.DoesNotExist:
        messages.error(request, 'Booking not found or not in confirmed status.')
        return redirect('expert:session_requests')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        import traceback
        traceback.print_exc()
        return redirect('expert:session_requests')

def complete_session_process(request, therapist, booking, client_name, with_note=False):
    """Process the actual session completion"""
    from expert.models import TimeSlot, TherapistSettings
    
    # Update booking status
    booking.status = 'completed'
    booking.completed_at = timezone.now()
    booking.save()
    
    # Update TimeSlot status
    time_slot = TimeSlot.objects.filter(
        therapist=therapist,
        date=booking.booking_date,
        start_time=booking.booking_time
    ).first()
    
    if time_slot:
        time_slot.is_booked = True
        time_slot.is_available = False
        time_slot.save()
    
    # Update therapist statistics and earnings
    try:
        settings, created = TherapistSettings.objects.get_or_create(therapist=therapist)
        
        # Update total sessions count
        settings.total_sessions += 1
        
        # Update earnings if consultation fee is set
        if hasattr(booking, 'consultation_fee') and booking.consultation_fee:
            settings.total_earnings += booking.consultation_fee
        elif settings.consultation_fee:
            settings.total_earnings += settings.consultation_fee
        
        settings.save()
        
        note_message = " and notes added" if with_note else ""
        messages.success(request, f'Session with {client_name} marked as completed{note_message}. Earnings updated.')
        
    except Exception as e:
        note_message = " and notes added" if with_note else ""
        messages.warning(request, f'Session marked as completed{note_message}, but earnings could not be updated: {str(e)}')
    
    return redirect('expert:session_requests')

def complete_session_process(request, therapist, booking, client_name, with_note=False):
    """Process the actual session completion"""
    from expert.models import TimeSlot, TherapistSettings
    
    # Update booking status
    booking.status = 'completed'
    booking.completed_at = timezone.now()
    booking.save()
    
    # Update TimeSlot status
    time_slot = TimeSlot.objects.filter(
        therapist=therapist,
        date=booking.booking_date,
        start_time=booking.booking_time
    ).first()
    
    if time_slot:
        time_slot.is_booked = True
        time_slot.is_available = False
        time_slot.save()
    
    # Update therapist statistics and earnings
    try:
        settings, created = TherapistSettings.objects.get_or_create(therapist=therapist)
        
        # Update total sessions count
        settings.total_sessions += 1
        
        # Update earnings if consultation fee is set
        if hasattr(booking, 'consultation_fee') and booking.consultation_fee:
            settings.total_earnings += booking.consultation_fee
        elif settings.consultation_fee:
            settings.total_earnings += settings.consultation_fee
        
        settings.save()
        
        note_message = " and notes added" if with_note else ""
        messages.success(request, f'Session with {client_name} marked as completed{note_message}. Earnings updated.')
        
    except Exception as e:
        note_message = " and notes added" if with_note else ""
        messages.warning(request, f'Session marked as completed{note_message}, but earnings could not be updated: {str(e)}')
    
    return redirect('expert:session_requests')


@login_required
def start_session(request, booking_id):
    """Start a video session"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist, status='confirmed')
        
        # Check if session is for today or future
        if booking.booking_date < timezone.now().date():
            messages.warning(request, 'This session is from a past date. You can still join if the meeting link is active.')
        elif booking.booking_date == timezone.now().date():
            # Check if it's too early to join (more than 15 minutes before)
            session_datetime = timezone.datetime.combine(booking.booking_date, booking.booking_time)
            session_datetime = timezone.make_aware(session_datetime)
            time_diff = session_datetime - timezone.now()
            
            if time_diff.total_seconds() > 900:  # 15 minutes in seconds
                minutes_until = int(time_diff.total_seconds() / 60)
                messages.info(request, f'Session starts in {minutes_until} minutes. You can join closer to the start time.')
        
        # Generate meeting link if not exists
        if not booking.meeting_link:
            import uuid
            room_name = f"empathyq-{booking.id}-{uuid.uuid4().hex[:8]}"
            booking.meeting_link = f"https://meet.jit.si/{room_name}"
            booking.save()
        
        # Redirect to meeting link
        return redirect(booking.meeting_link)
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('expert:session_requests')
    except SessionBooking.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return redirect('expert:session_requests')
    except Exception as e:
        messages.error(request, f'Error starting session: {str(e)}')
        return redirect('expert:session_requests')

# ==================== TODAY SESSIONS FUNCTION ====================

# expert/views.py - Update today_sessions function

@login_required
def today_sessions(request):
    """View today's sessions for expert"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        today = timezone.now().date()
        
        # Get today's confirmed sessions
        confirmed_sessions = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date=today,
            status='confirmed'
        ).select_related('user', 'category').order_by('booking_time')
        
        # Get today's pending sessions
        pending_sessions = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date=today,
            status='pending'
        ).select_related('user', 'category').order_by('booking_time')
        
        # Get today's completed sessions (optional)
        completed_sessions = SessionBooking.objects.filter(
            therapist=therapist,
            booking_date=today,
            status='completed'
        ).select_related('user', 'category').order_by('booking_time')
        
        # Ensure meeting links exist for confirmed sessions
        for session in confirmed_sessions:
            if not session.meeting_link:
                session.generate_meeting_link()
        
        # Get today's TimeSlot bookings (if using TimeSlot model)
        try:
            from .models import TimeSlot
            today_slots = TimeSlot.objects.filter(
                therapist=therapist,
                date=today,
                is_booked=True
            ).select_related('booking_detail__seeker')
        except:
            today_slots = []
        
        context = {
            'today_sessions': confirmed_sessions,
            'pending_today': pending_sessions,
            'completed_today': completed_sessions,
            'today_slots': today_slots,
            'today_date': today,
            'total_today': confirmed_sessions.count() + pending_sessions.count(),
        }
        
        return render(request, 'expert/today_sessions.html', context)
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('accounts:expert_dashboard')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('accounts:expert_dashboard')
# ==================== UPDATED MANAGE AVAILABILITY FUNCTION ====================

@login_required
def manage_availability(request):
    """Manage expert availability - Cinema style booking system"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('home')
    
    today = timezone.now().date()
    
    # Get or create settings
    settings, created = TherapistSettings.objects.get_or_create(therapist=therapist)
    
    # Get existing availability (working hours)
    availabilities = Availability.objects.filter(
        therapist=therapist,
        is_active=True
    ).order_by('day_of_week', 'start_time')
    
    # Get time off requests
    time_offs = TimeOff.objects.filter(therapist=therapist).order_by('-created_at')
    
    # Get upcoming available slots
    upcoming_slots = TimeSlot.objects.filter(
        therapist=therapist,
        date__gte=today,
        is_booked=False,
        is_blocked=False
    ).order_by('date', 'start_time')[:20]
    
    # Get booked slots
    booked_slots = TimeSlot.objects.filter(
        therapist=therapist,
        date__gte=today,
        is_booked=True
    ).select_related('booking_detail__seeker').order_by('date', 'start_time')[:10]
    
    # Days of week choices
    days_of_week = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Add working hours
        if action == 'add_availability':
            try:
                day_of_week = int(request.POST.get('day_of_week'))
                start_time = datetime.datetime.strptime(request.POST.get('start_time'), '%H:%M').time()
                end_time = datetime.datetime.strptime(request.POST.get('end_time'), '%H:%M').time()
                
                if start_time >= end_time:
                    messages.error(request, 'End time must be after start time.')
                    return redirect('expert:manage_availability')
                
                # Check for overlapping
                overlapping = Availability.objects.filter(
                    therapist=therapist,
                    day_of_week=day_of_week
                ).filter(
                    Q(start_time__lt=end_time) & Q(end_time__gt=start_time)
                ).exists()
                
                if overlapping:
                    messages.error(request, 'This time overlaps with existing availability.')
                    return redirect('expert:manage_availability')
                
                Availability.objects.create(
                    therapist=therapist,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True
                )
                
                messages.success(request, 'Working hours added successfully!')
            except (ValueError, KeyError) as e:
                messages.error(request, f'Invalid data: {str(e)}')
        
        # Delete availability
        elif action == 'delete_availability':
            slot_id = request.POST.get('slot_id')
            try:
                availability = Availability.objects.get(id=slot_id, therapist=therapist)
                availability.delete()
                messages.success(request, 'Working hours removed.')
            except Availability.DoesNotExist:
                messages.error(request, 'Availability not found.')
        
        # Generate time slots
        elif action == 'generate_slots':
            try:
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                
                if start_date:
                    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                else:
                    start_date = today
                
                if end_date:
                    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    end_date = start_date + timedelta(days=30)
                
                slots_created = 0
                current_date = start_date
                
                while current_date <= end_date:
                    day_of_week = current_date.weekday()
                    day_availabilities = availabilities.filter(day_of_week=day_of_week)
                    
                    for availability in day_availabilities:
                        slot, created = TimeSlot.objects.get_or_create(
                            therapist=therapist,
                            date=current_date,
                            start_time=availability.start_time,
                            defaults={
                                'end_time': availability.end_time,
                                'duration_minutes': settings.session_duration,
                                'is_available': True,
                                'availability': availability
                            }
                        )
                        if created:
                            slots_created += 1
                    
                    current_date += timedelta(days=1)
                
                messages.success(request, f'Successfully generated {slots_created} time slots!')
            except Exception as e:
                messages.error(request, f'Error generating slots: {str(e)}')
        
        # Block a slot
        elif action == 'block_slot':
            slot_id = request.POST.get('slot_id')
            try:
                slot = TimeSlot.objects.get(id=slot_id, therapist=therapist)
                if not slot.is_booked:
                    slot.block()
                    messages.success(request, f'Slot has been blocked.')
                else:
                    messages.error(request, 'Cannot block a booked slot.')
            except TimeSlot.DoesNotExist:
                messages.error(request, 'Slot not found.')
        
        # Unblock a slot
        elif action == 'unblock_slot':
            slot_id = request.POST.get('slot_id')
            try:
                slot = TimeSlot.objects.get(id=slot_id, therapist=therapist)
                slot.unblock()
                messages.success(request, f'Slot is now available.')
            except TimeSlot.DoesNotExist:
                messages.error(request, 'Slot not found.')
        
        # Update settings
        elif action == 'update_settings':
            try:
                if request.POST.get('consultation_fee'):
                    settings.consultation_fee = request.POST.get('consultation_fee')
                if request.POST.get('advance_booking_days'):
                    settings.advance_booking_days = request.POST.get('advance_booking_days')
                if request.POST.get('session_duration'):
                    settings.session_duration = request.POST.get('session_duration')
                if request.POST.get('buffer_time'):
                    settings.buffer_time = request.POST.get('buffer_time')
                
                settings.video_enabled = request.POST.get('video_enabled') == 'on'
                settings.instant_booking = request.POST.get('instant_booking') == 'on'
                settings.save()
                
                messages.success(request, 'Settings updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating settings: {str(e)}')
        
        # Add time off
        elif action == 'add_time_off':
            try:
                start_date = datetime.datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
                reason = request.POST.get('reason', '')
                
                if start_date > end_date:
                    messages.error(request, 'End date must be after start date.')
                    return redirect('expert:manage_availability')
                
                overlapping = TimeOff.objects.filter(
                    therapist=therapist,
                    start_date__lte=end_date,
                    end_date__gte=start_date
                ).exists()
                
                if overlapping:
                    messages.error(request, 'This period overlaps with existing time off.')
                    return redirect('expert:manage_availability')
                
                TimeOff.objects.create(
                    therapist=therapist,
                    start_date=start_date,
                    end_date=end_date,
                    reason=reason,
                    status='pending'
                )
                
                messages.success(request, 'Time off request submitted.')
            except (ValueError, KeyError) as e:
                messages.error(request, f'Invalid date format: {str(e)}')
        
        # Cancel time off
        elif action == 'cancel_time_off':
            timeoff_id = request.POST.get('timeoff_id')
            try:
                time_off = TimeOff.objects.get(id=timeoff_id, therapist=therapist)
                if time_off.status == 'pending':
                    time_off.delete()
                    messages.success(request, 'Time off request cancelled.')
                else:
                    messages.error(request, 'Cannot cancel processed request.')
            except TimeOff.DoesNotExist:
                messages.error(request, 'Request not found.')
    
    context = {
        'availabilities': availabilities,
        'time_offs': time_offs,
        'upcoming_slots': upcoming_slots,
        'booked_slots': booked_slots,
        'days_of_week': days_of_week,
        'settings': settings,
        'today': today,
    }
    
    return render(request, 'expert/manage_availability.html', context)

# ==================== PROFILE MANAGEMENT FUNCTIONS ====================

@login_required
def profile_settings(request):
    """Update expert profile settings"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings, created = ExpertProfileSettings.objects.get_or_create(therapist=therapist)
        
        specialization_choices = [
            ('clinical', 'Clinical Psychology'),
            ('counseling', 'Counseling Psychology'),
            ('child', 'Child Psychology'),
            ('adolescent', 'Adolescent Psychology'),
            ('forensic', 'Forensic Psychology'),
            ('health', 'Health Psychology'),
            ('neuro', 'Neuropsychology'),
            ('organizational', 'Organizational Psychology'),
            ('school', 'School Psychology'),
            ('social', 'Social Psychology'),
            ('sports', 'Sports Psychology'),
            ('trauma', 'Trauma Psychology'),
            ('addiction', 'Addiction Counseling'),
            ('marriage', 'Marriage & Family Therapy'),
            ('career', 'Career Counseling'),
            ('grief', 'Grief Counseling'),
            ('eating', 'Eating Disorders'),
            ('ocd', 'OCD & Anxiety Disorders'),
            ('ptsd', 'PTSD & Trauma'),
            ('depression', 'Depression & Mood Disorders'),
        ]
        
        expertise_choices = [
            ('anxiety', 'Anxiety Management'),
            ('depression', 'Depression Treatment'),
            ('stress', 'Stress Management'),
            ('trauma', 'Trauma Recovery'),
            ('ptsd', 'PTSD Treatment'),
            ('ocd', 'OCD Treatment'),
            ('panic', 'Panic Disorders'),
            ('phobias', 'Phobia Treatment'),
            ('bipolar', 'Bipolar Disorder'),
            ('eating', 'Eating Disorders'),
            ('addiction', 'Addiction Recovery'),
            ('relationships', 'Relationship Issues'),
            ('family', 'Family Conflict'),
            ('parenting', 'Parenting Support'),
            ('adolescent', 'Adolescent Issues'),
            ('grief', 'Grief & Loss'),
            ('self_esteem', 'Self Esteem'),
            ('anger', 'Anger Management'),
            ('sleep', 'Sleep Disorders'),
            ('chronic', 'Chronic Pain/Illness'),
            ('workplace', 'Workplace Stress'),
            ('burnout', 'Professional Burnout'),
            ('life_transition', 'Life Transitions'),
            ('identity', 'Identity Issues'),
            ('cultural', 'Cultural Issues'),
            ('lgbtq', 'LGBTQ+ Support'),
        ]
        
        if request.method == 'POST':
            if 'profile_photo' in request.FILES:
                profile_settings.profile_photo = request.FILES['profile_photo']
            
            if 'cover_photo' in request.FILES:
                profile_settings.cover_photo = request.FILES['cover_photo']
            
            if hasattr(therapist, 'bio'):
                therapist.bio = request.POST.get('about_me', therapist.bio)
            
            if hasattr(therapist, 'specialization'):
                therapist.specialization = request.POST.get('specialization', therapist.specialization)
            
            therapist.save()
            
            profile_settings.professional_title = request.POST.get('professional_title', '')
            profile_settings.about_me = request.POST.get('about_me', '')
            profile_settings.experience_years = request.POST.get('experience_years', 0)
            profile_settings.consultation_fee = request.POST.get('consultation_fee', 50)
            profile_settings.session_duration = request.POST.get('session_duration', 60)
            profile_settings.video_enabled = request.POST.get('video_enabled') == 'on'
            profile_settings.chat_enabled = request.POST.get('chat_enabled') == 'on'
            profile_settings.phone_enabled = request.POST.get('phone_enabled') == 'on'
            profile_settings.instant_booking = request.POST.get('instant_booking') == 'on'
            profile_settings.advance_booking_days = request.POST.get('advance_booking_days', 30)
            profile_settings.cancellation_policy = request.POST.get('cancellation_policy', '')
            profile_settings.show_email = request.POST.get('show_email') == 'on'
            profile_settings.show_phone = request.POST.get('show_phone') == 'on'
            profile_settings.is_profile_public = request.POST.get('is_profile_public') == 'on'
            profile_settings.specializations = request.POST.get('specializations', '')
            profile_settings.expertise_areas = request.POST.get('expertise_areas', '')
            profile_settings.languages = request.POST.get('languages', '')
            profile_settings.qualifications = request.POST.get('qualifications', '')
            
            phone_numbers = []
            phone_number_inputs = request.POST.getlist('phone_numbers[]')
            phone_type_inputs = request.POST.getlist('phone_types[]')
            primary_phones = request.POST.getlist('primary_phones[]')
            
            for i in range(len(phone_number_inputs)):
                if phone_number_inputs[i]:
                    phone_numbers.append({
                        'number': phone_number_inputs[i],
                        'type': phone_type_inputs[i] if i < len(phone_type_inputs) else 'mobile',
                        'is_primary': str(i) in primary_phones
                    })
            
            profile_settings.phone_numbers = phone_numbers
            profile_settings.save()
            
            messages.success(request, 'Profile settings updated successfully!')
            return redirect('expert:profile_settings')
        
        selected_languages = []
        if profile_settings.languages:
            selected_languages = [lang.strip() for lang in profile_settings.languages.split(',') if lang.strip()]
        
        existing_specializations = []
        if profile_settings.specializations:
            existing_specializations = [s.strip() for s in profile_settings.specializations.split(',') if s.strip()]
        
        existing_expertise = []
        if profile_settings.expertise_areas:
            existing_expertise = [e.strip() for e in profile_settings.expertise_areas.split(',') if e.strip()]
        
        context = {
            'profile': profile_settings,
            'therapist': therapist,
            'specialization_choices': specialization_choices,
            'expertise_choices': expertise_choices,
            'selected_languages': selected_languages,
            'existing_specializations': existing_specializations,
            'existing_expertise': existing_expertise,
        }
        
    except Therapist.DoesNotExist:
        messages.warning(request, 'Therapist profile not found.')
        context = {}
    
    return render(request, 'expert/profile_settings.html', context)

# ==================== PHONE NUMBER MANAGEMENT ====================

@login_required
@require_POST
def add_phone_number(request):
    """Add a new phone number"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings, created = ExpertProfileSettings.objects.get_or_create(therapist=therapist)
        
        phone_number = request.POST.get('phone_number')
        phone_type = request.POST.get('phone_type', 'mobile')
        is_primary = request.POST.get('is_primary') == 'on'
        
        if not phone_number:
            messages.error(request, 'Phone number is required.')
            return redirect('expert:profile_settings')
        
        phone_numbers = profile_settings.phone_numbers or []
        if not isinstance(phone_numbers, list):
            phone_numbers = []
        
        if is_primary:
            for phone in phone_numbers:
                if isinstance(phone, dict):
                    phone['is_primary'] = False
        
        new_phone = {
            'number': phone_number,
            'type': phone_type,
            'is_primary': is_primary
        }
        phone_numbers.append(new_phone)
        
        profile_settings.phone_numbers = phone_numbers
        profile_settings.save()
        
        messages.success(request, 'Phone number added successfully!')
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error adding phone number: {str(e)}')
    
    return redirect('expert:profile_settings')

@login_required
def delete_phone_number(request, phone_id):
    """Delete a phone number"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings = ExpertProfileSettings.objects.get(therapist=therapist)
        
        phone_numbers = profile_settings.phone_numbers or []
        if not isinstance(phone_numbers, list):
            phone_numbers = []
        
        phone_id = int(phone_id)
        
        if 0 <= phone_id < len(phone_numbers):
            phone_numbers.pop(phone_id)
            profile_settings.phone_numbers = phone_numbers
            profile_settings.save()
            messages.success(request, f'Phone number removed successfully!')
        else:
            messages.error(request, 'Phone number not found.')
            
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error removing phone number: {str(e)}')
    
    return redirect('expert:profile_settings')

# ==================== SPECIALIZATION MANAGEMENT ====================

@login_required
@require_POST
def add_specialization(request):
    """Add a specialization"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings, created = ExpertProfileSettings.objects.get_or_create(therapist=therapist)
        
        specialization = request.POST.get('specialization')
        
        if not specialization:
            messages.error(request, 'Specialization is required.')
            return redirect('expert:profile_settings')
        
        specializations = []
        if profile_settings.specializations:
            specializations = [s.strip() for s in profile_settings.specializations.split(',') if s.strip()]
        
        if specialization not in specializations:
            specializations.append(specialization)
            profile_settings.specializations = ', '.join(specializations)
            profile_settings.save()
            messages.success(request, 'Specialization added successfully!')
        else:
            messages.warning(request, 'Specialization already exists.')
            
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error adding specialization: {str(e)}')
    
    return redirect('expert:profile_settings')

@login_required
def remove_specialization(request, spec_id):
    """Remove a specialization"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings = ExpertProfileSettings.objects.get(therapist=therapist)
        
        specializations = []
        if profile_settings.specializations:
            specializations = [s.strip() for s in profile_settings.specializations.split(',') if s.strip()]
        
        spec_id = int(spec_id)
        
        if 0 <= spec_id < len(specializations):
            specializations.pop(spec_id)
            profile_settings.specializations = ', '.join(specializations)
            profile_settings.save()
            messages.success(request, f'Specialization removed successfully!')
        else:
            messages.error(request, 'Specialization not found.')
            
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error removing specialization: {str(e)}')
    
    return redirect('expert:profile_settings')

# ==================== EXPERTISE MANAGEMENT ====================

@login_required
@require_POST
def add_expertise(request):
    """Add an expertise area"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings, created = ExpertProfileSettings.objects.get_or_create(therapist=therapist)
        
        expertise = request.POST.get('expertise')
        
        if not expertise:
            messages.error(request, 'Expertise area is required.')
            return redirect('expert:profile_settings')
        
        expertise_areas = []
        if profile_settings.expertise_areas:
            expertise_areas = [e.strip() for e in profile_settings.expertise_areas.split(',') if e.strip()]
        
        if expertise not in expertise_areas:
            expertise_areas.append(expertise)
            profile_settings.expertise_areas = ', '.join(expertise_areas)
            profile_settings.save()
            messages.success(request, 'Expertise area added successfully!')
        else:
            messages.warning(request, 'Expertise area already exists.')
            
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error adding expertise area: {str(e)}')
    
    return redirect('expert:profile_settings')

@login_required
def remove_expertise(request, expertise_id):
    """Remove an expertise area"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        profile_settings = ExpertProfileSettings.objects.get(therapist=therapist)
        
        expertise_areas = []
        if profile_settings.expertise_areas:
            expertise_areas = [e.strip() for e in profile_settings.expertise_areas.split(',') if e.strip()]
        
        expertise_id = int(expertise_id)
        
        if 0 <= expertise_id < len(expertise_areas):
            expertise_areas.pop(expertise_id)
            profile_settings.expertise_areas = ', '.join(expertise_areas)
            profile_settings.save()
            messages.success(request, f'Expertise area removed successfully!')
        else:
            messages.error(request, 'Expertise area not found.')
            
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
    except Exception as e:
        messages.error(request, f'Error removing expertise area: {str(e)}')
    
    return redirect('expert:profile_settings')

# ==================== PUBLIC PROFILE VIEW ====================





@login_required
def public_profile(request, therapist_id=None):
    """View public profile of an expert"""
    try:
        if therapist_id:
            therapist = get_object_or_404(Therapist, id=therapist_id)
        else:
            therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        
        profile_settings = ExpertProfileSettings.objects.filter(therapist=therapist).first()
        
        # ===== FIXED: Import Review model and filter approved reviews =====
        from user.models import Review  # Add this import at the top of the function
        
        # Get only approved reviews
        reviews = Review.objects.filter(
            therapist=therapist, 
            is_approved=True
        ).order_by('-created_at')
        
        # ===== NEW CODE: Get available time slots for this expert =====
        from datetime import datetime, timedelta
        from expert.models import TimeSlot
        
        today = timezone.now().date()
        available_slots = TimeSlot.objects.filter(
            therapist=therapist,
            date__gte=today,
            is_available=True,
            is_booked=False,
            is_blocked=False
        ).order_by('date', 'start_time')[:20]  # Show next 20 available slots
        
        # Group slots by date for better display
        slots_by_date = {}
        for slot in available_slots:
            date_str = slot.date.strftime('%Y-%m-%d')
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(slot)
        # ===== END NEW CODE =====
        
        avg_rating = 0
        if reviews.exists():
            avg_rating = sum(r.rating for r in reviews) / reviews.count()
        
        total_sessions = SessionBooking.objects.filter(
            therapist=therapist, 
            status='completed'
        ).count()
        
        specializations_list = []
        if hasattr(therapist, 'specialization') and therapist.specialization:
            specializations_list = [s.strip() for s in therapist.specialization.split(',') if s.strip()]
        
        expertise_list = []
        if profile_settings and profile_settings.expertise_areas:
            expertise_list = [exp.strip() for exp in profile_settings.expertise_areas.split(',') if exp.strip()]
        
        languages_list = []
        if profile_settings and profile_settings.languages:
            languages_list = [lang.strip() for lang in profile_settings.languages.split(',') if lang.strip()]
        
        qualifications_list = []
        if profile_settings and profile_settings.qualifications:
            qualifications_list = [qual.strip() for qual in profile_settings.qualifications.split('\n') if qual.strip()]
        
        phone_numbers = []
        if profile_settings and profile_settings.phone_numbers:
            if isinstance(profile_settings.phone_numbers, list):
                phone_numbers = profile_settings.phone_numbers
            elif isinstance(profile_settings.phone_numbers, str):
                try:
                    phone_numbers = json.loads(profile_settings.phone_numbers)
                except:
                    phone_numbers = []
        
        context = {
            'therapist': therapist,
            'profile': profile_settings,
            'reviews': reviews,
            'avg_rating': round(avg_rating, 1),
            'total_reviews': reviews.count(),
            'total_sessions': total_sessions,
            'is_owner': request.user.is_authenticated and therapist.name == (request.user.get_full_name() or request.user.username),
            'specializations_list': specializations_list,
            'expertise_list': expertise_list,
            'languages_list': languages_list,
            'qualifications_list': qualifications_list,
            'phone_numbers': phone_numbers,
            # ===== NEW: Add slots to context =====
            'available_slots': available_slots,
            'slots_by_date': slots_by_date,
        }
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('accounts:expert_dashboard')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('accounts:expert_dashboard')
    
    return render(request, 'expert/profile.html', context)

# ==================== SESSION MANAGEMENT FUNCTIONS ====================

@login_required
def start_session(request, booking_id):
    """Start a video session"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist)
        
        if booking.status != 'confirmed':
            messages.error(request, 'This session is not confirmed yet.')
            return redirect('expert:today_sessions')
        
        if not booking.meeting_link:
            room_name = f"empathyq-{booking.id}-{uuid.uuid4().hex[:8]}"
            booking.meeting_link = f"https://meet.jit.si/{room_name}"
            booking.save()
        
        return redirect(booking.meeting_link)
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('accounts:expert_dashboard')

@login_required
def feedback(request, booking_id):
    """Submit feedback for a completed session"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        booking = get_object_or_404(SessionBooking, id=booking_id, therapist=therapist)
        
        if request.method == 'POST':
            rating = request.POST.get('rating')
            comment = request.POST.get('comment', '')
            
            Review.objects.create(
                therapist=therapist,
                user=booking.user,
                booking=booking,
                rating=rating,
                comment=comment
            )
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('expert:earnings')
        
        context = {
            'booking': booking,
        }
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('accounts:expert_dashboard')
    
    return render(request, 'expert/feedback.html', context)

@login_required
def analytics(request):
    """Expert analytics dashboard"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        
        total_sessions = SessionBooking.objects.filter(therapist=therapist).count()
        completed_sessions = SessionBooking.objects.filter(therapist=therapist, status='completed').count()
        cancelled_sessions = SessionBooking.objects.filter(therapist=therapist, status='cancelled').count()
        
        reviews = Review.objects.filter(therapist=therapist)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        total_reviews = reviews.count()
        
        monthly_sessions = SessionBooking.objects.filter(
            therapist=therapist,
            status='completed'
        ).extra({'month': "strftime('%%Y-%%m', booking_date)"}).values('month').annotate(
            count=Count('id'),
            earnings=Count('id') * 50
        ).order_by('-month')
        
        context = {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'cancelled_sessions': cancelled_sessions,
            'avg_rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'monthly_sessions': monthly_sessions,
        }
    except Therapist.DoesNotExist:
        context = {
            'total_sessions': 0,
            'completed_sessions': 0,
            'cancelled_sessions': 0,
            'avg_rating': 0,
            'total_reviews': 0,
            'monthly_sessions': [],
        }
        messages.warning(request, 'Therapist profile not found.')
    
    return render(request, 'expert/analytics.html', context)














# expert/views.py

# chat session
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
import json

# Import from your apps
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q, Max, OuterRef, Subquery, Count, DateTimeField
from django.utils import timezone
from user.models import SessionBooking, Therapist
from expert.models import ChatMessage, ExpertProfileSettings
import datetime

User = get_user_model()


@login_required
def chat_list(request):
    """Show all unique chat conversations with users"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        
        # Get all unique users who have booked sessions with this therapist
        # Using distinct() to ensure no duplicates
        booked_user_ids = SessionBooking.objects.filter(
            therapist=therapist,
            status__in=['confirmed', 'completed']
        ).values_list('user_id', flat=True).distinct()
        
        # Get users who have sent messages to this expert even without bookings
        message_sender_ids = ChatMessage.objects.filter(
            recipient=request.user
        ).values_list('sender_id', flat=True).distinct()
        
        # Get users who have received messages from this expert
        message_receiver_ids = ChatMessage.objects.filter(
            sender=request.user
        ).values_list('recipient_id', flat=True).distinct()
        
        # Combine all unique user IDs
        all_user_ids = set(list(booked_user_ids) + list(message_sender_ids) + list(message_receiver_ids))
        
        # Create a timezone-aware minimum datetime for sorting
        default_date = timezone.make_aware(
            datetime.datetime(1970, 1, 1),
            timezone.get_current_timezone()
        )
        
        conversations = []
        
        # FIXED: Process each unique user once
        for user_id in all_user_ids:
            try:
                user = User.objects.get(id=user_id)
                
                # Get last message between expert and this user
                last_message = ChatMessage.objects.filter(
                    Q(sender=user, recipient=request.user) |
                    Q(sender=request.user, recipient=user)
                ).order_by('-timestamp').first()
                
                # Count unread messages FROM this user TO expert
                unread_count = ChatMessage.objects.filter(
                    sender=user,
                    recipient=request.user,
                    is_read=False
                ).count()
                
                # Get the most recent booking with this user
                latest_booking = SessionBooking.objects.filter(
                    therapist=therapist,
                    user=user
                ).order_by('-booking_date', '-booking_time').first()
                
                # Count total completed sessions with this user
                total_sessions = SessionBooking.objects.filter(
                    therapist=therapist,
                    user=user,
                    status='completed'
                ).count()
                
                # Get user initials for avatar
                if user.get_full_name():
                    name_parts = user.get_full_name().split()
                    if len(name_parts) >= 2:
                        initials = name_parts[0][0] + name_parts[-1][0]
                    else:
                        initials = name_parts[0][0] if name_parts else user.username[0]
                else:
                    initials = user.username[0] if user.username else 'U'
                
                # Check if user has ever booked a session
                has_booked = SessionBooking.objects.filter(
                    therapist=therapist,
                    user=user
                ).exists()
                
                # FIXED: Properly structure the conversation data
                conversations.append({
                    'user': user,
                    'user_id': user.id,  # Explicitly include user_id for URL
                    'last_message': last_message,
                    'last_message_time': last_message.timestamp if last_message else None,
                    'unread_count': unread_count,
                    'latest_booking': latest_booking,
                    'total_sessions': total_sessions,
                    'has_booked_sessions': has_booked,
                    'initials': initials.upper()[:2],  # Ensure max 2 characters
                })
                
            except User.DoesNotExist:
                continue
        
        # FIXED: Improved sorting logic
        # First by unread count (higher first), then by last message time (most recent first)
        def sort_key(conv):
            # Get timestamp or default for sorting
            timestamp = conv['last_message_time'] or default_date
            
            # Create a tuple for sorting:
            # - First element: negative unread_count (so higher unread comes first)
            # - Second element: timestamp (most recent first)
            return (-conv['unread_count'], -timestamp.timestamp())
        
        # Sort conversations
        conversations.sort(key=sort_key)
        
        # Calculate total unread messages
        total_unread = sum(c['unread_count'] for c in conversations)
        
        context = {
            'conversations': conversations,
            'total_unread': total_unread,
            'therapist': therapist,
        }
        
        return render(request, 'expert/chat_list.html', context)
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found. Please contact administrator.')
        return redirect('accounts:expert_dashboard')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('accounts:expert_dashboard')

@login_required
def chat_room(request, user_id):
    """Chat room for expert to talk with a specific user"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        user = get_object_or_404(User, id=user_id)
        
        # Verify that this user has booked with the therapist
        has_booked = SessionBooking.objects.filter(
            therapist=therapist,
            user=user,
            status__in=['confirmed', 'completed']
        ).exists()
        
        if not has_booked:
            messages.error(request, 'You can only chat with users who have booked sessions with you.')
            return redirect('expert:chat_list')
        
        # Get all messages between expert and user using ChatMessage model
        messages_list = ChatMessage.objects.filter(
            Q(sender=request.user, recipient=user) |
            Q(sender=user, recipient=request.user)
        ).order_by('timestamp')
        
        # Mark messages as read
        unread_messages = messages_list.filter(
            sender=user,
            recipient=request.user,
            is_read=False
        )
        unread_messages.update(is_read=True)
        
        # Get user's booking info
        bookings = SessionBooking.objects.filter(
            therapist=therapist,
            user=user
        ).order_by('-booking_date')
        
        # Get user initials for avatar
        if user.get_full_name():
            name_parts = user.get_full_name().split()
            if len(name_parts) >= 2:
                user_initials = name_parts[0][0] + name_parts[1][0]
            else:
                user_initials = name_parts[0][0] if name_parts else user.username[0]
        else:
            user_initials = user.username[0] if user.username else 'U'
        
        context = {
            'chat_user': user,
            'messages': messages_list,
            'bookings': bookings,
            'therapist': therapist,
            'user_initials': user_initials.upper(),
        }
        
        return render(request, 'expert/chat_room.html', context)
        
    except Therapist.DoesNotExist:
        messages.error(request, 'Therapist profile not found.')
        return redirect('accounts:expert_dashboard')


@login_required
@csrf_exempt
def send_message(request):
    """Send a message via AJAX using ChatMessage model"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            message_text = data.get('message')
            
            if not user_id or not message_text:
                return JsonResponse({'success': False, 'error': 'Missing data'})
            
            user = get_object_or_404(User, id=user_id)
            
            # Create message using ChatMessage model
            message = ChatMessage.objects.create(
                sender=request.user,
                recipient=user,
                message=message_text,
                is_admin_reply=True  # Mark as expert reply
            )
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'time': message.timestamp.strftime('%H:%M'),
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def get_messages(request, user_id):
    """Get messages for AJAX refresh using ChatMessage model"""
    try:
        therapist = Therapist.objects.get(name=request.user.get_full_name() or request.user.username)
        user = get_object_or_404(User, id=user_id)
        
        messages_list = ChatMessage.objects.filter(
            Q(sender=request.user, recipient=user) |
            Q(sender=user, recipient=request.user)
        ).order_by('timestamp')
        
        messages_data = [{
            'id': msg.id,
            'message': msg.message,
            'time': msg.timestamp.strftime('%H:%M'),
            'is_me': msg.sender == request.user,
            'is_read': msg.is_read,
            'sender_name': 'You' if msg.sender == request.user else (user.get_full_name() or user.username),
        } for msg in messages_list]
        
        return JsonResponse({'messages': messages_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
















