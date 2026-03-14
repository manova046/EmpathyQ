from django.urls import path
from . import views


app_name = 'expert'

urlpatterns = [
    # Session Management
    path('session-requests/', views.session_requests, name='session_requests'),
    path('approve-session/<int:booking_id>/', views.approve_session, name='approve_session'),
    path('reject-session/<int:booking_id>/', views.reject_session, name='reject_session'),
    path('complete-session/<int:booking_id>/', views.complete_session, name='complete_session'),
    path('today-sessions/', views.today_sessions, name='today_sessions'),
    path('start-session/<int:booking_id>/', views.start_session, name='start_session'),
    
    # Availability & Schedule
    path('manage-availability/', views.manage_availability, name='manage_availability'),
    # Removed slot-management as it doesn't exist in views
    
    # Profile Management
    path('profile-settings/', views.profile_settings, name='profile_settings'),
    path('profile/', views.public_profile, name='my_profile'),
    path('profile/<int:therapist_id>/', views.public_profile, name='public_profile'),
    
    # Phone Number Management
    path('profile/phone/add/', views.add_phone_number, name='add_phone_number'),
    path('profile/phone/delete/<int:phone_id>/', views.delete_phone_number, name='delete_phone_number'),
    
    # Specialization Management
    path('profile/specialization/add/', views.add_specialization, name='add_specialization'),
    path('profile/specialization/remove/<int:spec_id>/', views.remove_specialization, name='remove_specialization'),
    
    # Expertise Management
    path('profile/expertise/add/', views.add_expertise, name='add_expertise'),
    path('profile/expertise/remove/<int:expertise_id>/', views.remove_expertise, name='remove_expertise'),
    
    # Reviews & Feedback
    path('feedback/<int:booking_id>/', views.feedback, name='feedback'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),




      # Chat URLs - using views directly since functions are in views.py
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    path('chat/send/', views.send_message, name='send_message'),
    path('chat/messages/<int:user_id>/', views.get_messages, name='get_messages'),



# expert/urls.py
path('complete-session/<int:booking_id>/', views.complete_session, name='complete_session'),

# Analytics
path('analytics/', views.analytics, name='analytics'),
]