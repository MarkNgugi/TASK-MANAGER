from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('redirect/', redirect_view, name='redirect_view'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('user-dashboard/', user_dashboard, name='user_dashboard'),
    path('logout/', logout_view, name='logout'),
    

    path('manage-tasks/', manage_tasks, name='managetasks'),
    # Task URLs
    path('my-tasks/', user_tasks, name='user_tasks'),
    path('tasks/', task_list, name='task_list'),
    path('tasks/create/', create_task, name='create_task'),
    path('tasks/<int:pk>/edit/', edit_task, name='edit_task'),        
    path('tasks/<int:pk>/verify/', verify_task, name='verify_task'),

    path('task/<int:pk>/start/', start_task, name='start_task'),
    path('task/<int:pk>/complete/', complete_task, name='complete_task'),
    path('task/<int:pk>/', task_detail, name='task_detail'),
    path('tasks/delete/<int:task_id>/', delete_task, name='delete_task'),


    path('users/', users, name='users'),

    
    # Leaderboard
    path('user-leaderboard/', user_leaderboard, name='userleaderboard'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('profile/', user_profile, name='user_profile'),
    
]
