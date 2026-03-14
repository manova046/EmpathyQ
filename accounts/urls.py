from django.urls import path
from . import views

app_name = 'accounts' 

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/user/', views.user_register, name='user_register'),
    path('register/expert/', views.expert_register, name='expert_register'),
    path("dashboard/user/", views.user_dashboard, name="user_dashboard"),
    path('dashboard/expert/', views.expert_dashboard, name='expert_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('approve-expert/<int:expert_id>/', views.approve_expert, name='approve_expert'),
    path('reject-expert/<int:expert_id>/', views.reject_expert, name='reject_expert'),
    path('admin-support/chat/', views.admin_chat, name='admin_chat'),

    # ===== Block/Unblock URLs =====
    path('block/user/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('block/expert/<int:expert_id>/', views.block_expert, name='block_expert'),
    path('unblock/expert/<int:expert_id>/', views.unblock_expert, name='unblock_expert'),
    path('get-block-info/<int:user_id>/', views.get_block_info, name='get_block_info'),
    
    # ===== Blocked page =====
    path('blocked/', views.blocked_page, name='blocked_page'),

    # ===== Expert Support URLs =====
    path('expert/support/', views.expert_support, name='expert_support'),
    path('dashboard/admin/expert-support/', views.admin_expert_support, name='admin_expert_support'),
    path('api/get-expert-support-messages/', views.get_expert_support_messages, name='get_expert_support_messages'),
    path('api/send-expert-support-message/', views.send_expert_support_message, name='send_expert_support_message'),

    # ===== Platform Reviews URLs =====
    path('submit-platform-review/', views.submit_platform_review, name='submit_platform_review'),
    # FIXED: Changed from 'admin/' to 'dashboard/admin/' to avoid conflict with Django admin
    path('dashboard/admin/platform-reviews/', views.admin_platform_reviews, name='admin_platform_reviews'),
    path('dashboard/admin/approve-platform-review/<int:review_id>/', views.approve_platform_review, name='approve_platform_review'),
    path('dashboard/admin/reject-platform-review/<int:review_id>/', views.reject_platform_review, name='reject_platform_review'),
    path('dashboard/admin/toggle-featured-review/<int:review_id>/', views.toggle_featured_review, name='toggle_featured_review'),
]