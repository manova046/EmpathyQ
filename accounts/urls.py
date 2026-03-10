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


    # ===== FIXED: Block/Unblock URLs - removed 'admin/' prefix =====
    path('block/user/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock/user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    path('block/expert/<int:expert_id>/', views.block_expert, name='block_expert'),
    path('unblock/expert/<int:expert_id>/', views.unblock_expert, name='unblock_expert'),
    path('get-block-info/<int:user_id>/', views.get_block_info, name='get_block_info'),
    
    # ===== Blocked page =====
    path('blocked/', views.blocked_page, name='blocked_page'),
]