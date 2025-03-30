from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('redirect/', redirect_view, name='redirect_view'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('user-dashboard/', user_dashboard, name='user_dashboard'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    # Task URLs
    path('tasks/', task_list, name='task_list'),
    path('tasks/create/', create_task, name='create_task'),
    path('tasks/<int:pk>/edit/', edit_task, name='edit_task'),
    path('tasks/<int:pk>/complete/', complete_task, name='complete_task'),
    path('tasks/<int:pk>/verify/', verify_task, name='verify_task'),
    
    # Leaderboard
    path('leaderboard/', leaderboard, name='leaderboard'),
    
]
