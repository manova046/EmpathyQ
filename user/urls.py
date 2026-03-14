from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    # Emotional check-in URLs
    path(
        "emotional-checkin/",
        views.emotional_checkin,
        name="emotional_checkin"
    ),
    path(
        "emotional-checkin/result/<int:checkin_id>/",
        views.emotional_result,
        name="emotional_result"
    ),
    
    # Check-in history URLs
    path(
        "checkins/",
        views.checkin_history,
        name="checkin_history"
    ),
    path(
        "checkins/<int:checkin_id>/",
        views.checkin_detail,
        name="checkin_detail"
    ),
    
    # Session booking URLs
    path(
        'book-session/',
        views.book_session,
        name='book_session'
    ),
    path(
        'create-booking/',
        views.create_booking,
        name='create_booking'
    ),
    path(
        'my-sessions/',
        views.my_sessions,
        name='my_sessions'
    ),
    path('cancel-session/<int:booking_id>/', views.cancel_session, name='cancel_session'),
    
    # ===========================================
    # KEEP ORIGINAL ANONYMOUS CHAT URLs (Don't change these!)
    # ===========================================
    path('chat/', views.chat_support, name='chat'),  # Keep original
    path(
        'chat/join/<int:checkin_id>/',
        views.join_chat_queue,
        name='join_chat'
    ),
    path(
        'chat/searching/',
        views.searching_chat,
        name='searching_chat'
    ),
    path(
        'chat/room/<uuid:room_id>/',
        views.chat_room,
        name='chat_room'
    ),
    path(
        'chat/messages/<uuid:room_id>/',
        views.get_chat_messages,
        name='get_messages'
    ),
    path(
        'chat/send-message/',
        views.send_chat_message,
        name='send_message'
    ),
    path(
        'chat/end/',
        views.end_chat,
        name='end_chat'
    ),
    path(
        'chat/feedback/<uuid:room_id>/',
        views.chat_feedback,
        name='chat_feedback'
    ),
    path(
        'chat/leave/<uuid:room_id>/',
        views.leave_chat,
        name='leave_chat'
    ),
    path(
        'chat/history/',
        views.chat_history,
        name='chat_history'
    ),
    
    # ===========================================
    # ADD EXPERT CHAT URLs (New, won't conflict)
    # ===========================================
    path(
        'expert-chat/',
        views.expert_chat,
        name='expert_chat'
    ),
    path(
        'expert-chat/<int:expert_id>/',
        views.expert_chat,
        name='expert_chat_with_expert'
    ),
    path(
        'expert-chat/messages/<int:expert_id>/',
        views.get_expert_messages,
        name='expert_messages'
    ),
    path(
        'expert-chat/send/',
        views.send_expert_message,
        name='expert_send'
    ),
    
    # Progress tracking URLs
    path(
        'track-progress/',
        views.track_progress,
        name='track_progress'
    ),
    path(
        'progress-report/',
        views.progress_report,
        name='progress_report'
    ),
    
    # Task management URLs
    path(
        'complete-task/<int:assignment_id>/',
        views.complete_task,
        name='complete_task'
    ),
    
    # Games URLs
    path('games/<str:game_name>/', views.play_game, name='play_game'),
    path('api/save-score/', views.save_game_score, name='save_game_score'),
    path('api/get-scores/<str:game>/', views.get_game_scores, name='get_game_scores'),
    path('games/breathing/', views.play_game, {'game_name': 'breathing'}, name='play_breathing'),
    path('games/bubblepop/', views.play_game, {'game_name': 'bubblepop'}, name='play_bubblepop'),
    path('games/coloring/', views.play_game, {'game_name': 'coloring'}, name='play_coloring'),
     path('reschedule-session/', views.reschedule_session, name='reschedule_session'),
        # NEW: Add URLs for new games
    path('games/oddeven/', views.play_game, {'game_name': 'oddeven'}, name='play_oddeven'),
    path('games/sos/', views.play_game, {'game_name': 'sos'}, name='play_sos'),
      path('games/snake/', views.play_game, {'game_name': 'snake'}, name='play_snake'),


        # New note-related URLs
    path('my-notes/', views.my_notes, name='my_notes'),
    path('view-note/<int:note_id>/', views.view_note, name='view_note'),
    path('download-note/<int:note_id>/', views.download_note_attachment, name='download_note_attachment'),
    path('mark-note-read/<int:note_id>/', views.mark_note_as_read, name='mark_note_as_read'),
    path('print-note/<int:note_id>/', views.print_note, name='print_note'),


        # ===== NEW: Review URLs =====
    path('submit-review/', views.submit_review, name='submit_review'),
    path('get-session-details/<int:session_id>/', views.get_session_details, name='get_session_details'),



    # Payment URLs
    path('payment/initiate/<int:booking_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/success/<int:booking_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/<int:booking_id>/', views.payment_failed, name='payment_failed'),
    path('payment/retry/<int:booking_id>/', views.retry_payment, name='retry_payment'),
]