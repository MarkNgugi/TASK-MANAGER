from django.shortcuts import redirect,render,get_object_or_404
from django.contrib.auth import login, authenticate,logout
from django.db.models import Count, Q, Avg 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import *
from django.contrib import messages
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.timesince import timesince
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

class CustomLoginView(LoginView):
    template_name = 'myapp/login.html'
    
    def form_invalid(self, form):
        """Handle invalid form submissions with error message."""
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)

    def get_success_url(self):
        """Redirect users based on their role after successful login."""
        user = self.request.user
        if user.is_authenticated:
            if user.is_superuser or user.is_staff:  # Changed from is_admin to is_staff for Django's default
                return reverse_lazy('admin_dashboard')
        return reverse_lazy('user_dashboard')

@login_required
def redirect_view(request):
    if request.user.is_superuser or request.user.is_admin:
        return redirect('admin_dashboard')
    return redirect('user_dashboard')


@login_required
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    # Get all stats
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='pending').count()
    in_progress = Task.objects.filter(status='in_progress').count()
    active_users = CustomUser.objects.filter(is_admin=False).count()
    completed_tasks = Task.objects.filter(status='completed').count()
    
    # Get top performers with their verified task counts
    top_performers = CustomUser.objects.filter(is_admin=False).annotate(
        verified_count=Count('assigned_tasks', filter=Q(assigned_tasks__status='verified')),
        average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
    ).order_by('-points')[:5]
    
    # Get actual recent activities
    recent_activities = []
    
    # 1. Recently completed tasks
    recent_completed = Task.objects.filter(status='verified').order_by('-updated_at')[:3]
    for task in recent_completed:
        recent_activities.append({
            'message': f"User '{task.assigned_to.username}' completed task '{task.title}'",
            'timestamp': f"{timesince(task.updated_at)} ago",
            'icon': 'fas fa-check-circle'
        })
    
    # 2. Recently assigned tasks
    recent_assigned = Task.objects.order_by('-created_at')[:2]
    for task in recent_assigned:
        recent_activities.append({
            'message': f"You assigned task '{task.title}' to '{task.assigned_to.username}'",
            'timestamp': task.created_at,
            'icon': 'fas fa-tasks'
        })
    
    # 3. Recently rated tasks
    recent_rated = Task.objects.filter(rating__isnull=False).order_by('-updated_at')[:2]
    for task in recent_rated:
        recent_activities.append({
            'message': f"You rated task '{task.title}' with {task.rating} stars",
            'timestamp': task.updated_at,
            'icon': 'fas fa-star'
        })
    
    # Sort all activities by timestamp and take the most recent 5
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]
    
    context = {
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress':in_progress,
        'active_users': active_users,
        'completed_tasks': completed_tasks,
        'top_performers': top_performers,
        'recent_activities': recent_activities,
    }
    return render(request, 'myapp/admin_dashboard.html', context)

@login_required
def user_dashboard(request):
    if request.user.is_admin:
        return redirect('admin_dashboard')
    
    user = request.user
    
    # Get tasks and counts
    tasks = user.assigned_tasks.all().order_by('due_date')
    pending_count = tasks.filter(status='pending').count()
    in_progress_count = tasks.filter(status='in_progress').count()
    completed_count = tasks.filter(status__in=['completed', 'verified']).count()
    
    # Calculate actual average rating
    rating_info = user.assigned_tasks.filter(rating__isnull=False)\
                    .aggregate(
                        avg_rating=Avg('rating'),
                        rated_tasks=Count('id')
                    )
    user_rating = round(rating_info['avg_rating'] or 0, 1)
    
    # Calculate progress to next reward level
    points_needed = max(0, (user.points // 100 + 1) * 100 - user.points)
    progress = min(100, (user.points % 100))
    
    # Get reward level
    reward_level = f"Level {user.points // 100 + 1}"
    
    # Get recent activities from actual rated tasks
    recent_activities = []
    rated_tasks = user.assigned_tasks.filter(rating__isnull=False)\
                    .order_by('-created_at')[:3]
    
    for task in rated_tasks:
        recent_activities.append({
            'title': f'Received {task.rating * 10} points for "{task.title}"',
            'date': naturaltime(task.created_at),
            'icon': 'fas fa-coins'
        })
    
    # Add some default activities if not enough rated tasks
    if len(recent_activities) < 3:
        recent_activities.extend([
            {'title': 'Task "Update profile" marked as completed', 'date': '2 hours ago', 'icon': 'fas fa-check-circle'},
            {'title': 'Task "Write documentation" assigned', 'date': '3 days ago', 'icon': 'fas fa-tasks'},
        ][:3-len(recent_activities)])
    
    # Get top performers - UPDATED TO INCLUDE BOTH COMPLETED AND VERIFIED TASKS
    top_performers = CustomUser.objects.filter(is_admin=False)\
        .annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status__in=['completed', 'verified'])),
            average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
        )\
        .order_by('-points')[:10]
    
    # Find user's position
    user_position = None
    for i, performer in enumerate(top_performers, 1):
        if performer == user:
            user_position = i
            break
    
    context = {
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'progress': progress,
        'points_needed': points_needed,
        'reward_level': reward_level,
        'rewards_available': user.rewards,
        'top_performers': top_performers,
        'user_position': user_position,
        'user_completed': completed_count,
        'user_rating': user_rating,
        'recent_activities': recent_activities,
    }
    return render(request, 'myapp/user_dashboard.html', context)

@login_required
def manage_tasks(request):
    tasks = Task.objects.all().order_by('-created_at')
    users = CustomUser.objects.all()
    
    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    assigned_to_filter = request.GET.get('assigned_to')
    if assigned_to_filter:
        tasks = tasks.filter(assigned_to__id=assigned_to_filter)
    
    due_date_filter = request.GET.get('due_date')
    if due_date_filter:
        tasks = tasks.filter(due_date__date=due_date_filter)
    
    context = {
        'tasks': tasks,
        'users': users,
        'status_choices': Task.STATUS_CHOICES
    }
    return render(request, 'myapp/manage_tasks.html', context)


@login_required
def task_list(request):
    if request.user.is_admin:
        tasks = Task.objects.all().order_by('-created_at')
    else:
        tasks = request.user.assigned_tasks.all().order_by('-created_at')
    
    context = {
        'tasks': tasks,
        'is_admin': request.user.is_admin
    }
    return render(request, 'myapp/task_list.html', context)

@login_required
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            # Only set rating if the user is admin and provided a rating
            if not request.user.is_admin or not form.cleaned_data.get('rating'):
                task.rating = None
            task.save()
            return redirect('managetasks')
    else:
        form = TaskForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'myapp/task_form.html', context)

@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            # Only update rating if the user is admin and provided a rating
            if not request.user.is_admin or not form.cleaned_data.get('rating'):
                form.instance.rating = task.rating  # Keep existing rating
            form.save()
            return redirect('managetasks')
    else:
        form = TaskForm(instance=task, user=request.user)
    
    context = {
        'form': form,
        'task': task
    }
    return render(request, 'myapp/task_form.html', context)


@login_required
def delete_task(request, task_id):
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        task.delete()
        messages.success(request, 'Task deleted successfully')
        return redirect('managetasks')
    return redirect('managetasks')


CustomUser = get_user_model()
@login_required
def users(request):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    # Exclude admin users from the list
    users = CustomUser.objects.filter(is_admin=False).order_by('-date_joined')
    
    # Add completed tasks count to each user
    for user in users:
        user.completed_tasks = Task.objects.filter(
            assigned_to=user, 
            status='completed'
        ).count()
        user.in_progress_tasks = Task.objects.filter(
            assigned_to=user, 
            status='in_progress'
        ).count()
        user.pending_tasks = Task.objects.filter(
            assigned_to=user, 
            status='pending'
        ).count()
    
    # Initialize form outside of POST check
    form = CustomUserCreationForm()
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password('default123')  # Set default password
            user.save()
            messages.success(request, f"User {user.username} created successfully!")
            return redirect('users')
    
    context = {
        'users': users,
        'form': form
    }
    return render(request, 'myapp/users.html', context)

def edit_user(request, user_id):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('users')
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'myapp/edit_user.html', {
        'form': form,
        'user': user
    })

def delete_user(request, user_id):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        return redirect('users')
    
    return render(request, 'myapp/confirm_delete.html', {
        'user': user
    })

def reset_password(request, user_id):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        user.password = make_password('default123')
        user.save()
        messages.success(request, f'Password for {user.username} has been reset to default!')
        return redirect('users')
    
    return render(request, 'myapp/confirm_reset.html', {
        'user': user
    })

@login_required
def user_tasks(request):
    user = request.user
    tasks = user.assigned_tasks.all().order_by('due_date')
    
    # Handle filtering
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        if status_filter == 'completed':
            tasks = tasks.filter(status__in=['completed', 'verified'])
        else:
            tasks = tasks.filter(status=status_filter)
    
    # Count tasks by status (must be before filtering for accurate counts)
    task_counts = {
        'pending': user.assigned_tasks.filter(status='pending').count(),
        'in_progress': user.assigned_tasks.filter(status='in_progress').count(),
        'completed': user.assigned_tasks.filter(status__in=['completed', 'verified']).count(),
    }
    
    context = {
        'tasks': tasks,
        'task_counts': task_counts,
        'user': user,
        'status_filter': status_filter if status_filter else 'all'
    }
    return render(request, 'myapp/user_tasks.html', context)

@login_required
def user_leaderboard(request):
    # Get all non-admin users with their points, completed tasks, and average rating
    leaderboard_users = CustomUser.objects.filter(is_admin=False)\
        .annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status__in=['completed', 'verified'])),
            average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
        )\
        .order_by('-points')
    
    # Find current user's position
    user_position = None
    for i, user in enumerate(leaderboard_users, 1):
        if user == request.user:
            user_position = i
            break
    
    context = {
        'leaderboard_users': leaderboard_users,
        'user_position': user_position,
        'user_completed': request.user.assigned_tasks.filter(status__in=['completed', 'verified']).count(),
        'user_rating': request.user.assigned_tasks.filter(rating__isnull=False)\
                         .aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
    }
    return render(request, 'myapp/user_leaderboard.html', context)


from django.db.models import Count, Q, Avg

def leaderboard(request):
    # Get all non-admin users with their points and completed tasks count
    leaderboard_users = CustomUser.objects.filter(is_admin=False)\
        .annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status__in=['completed', 'verified'])),
            average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
        )\
        .order_by('-points')
    
    context = {
        'leaderboard': leaderboard_users,
    }
    return render(request, 'myapp/leaderboard.html', context)


@login_required
def start_task(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    if task.status == 'pending':
        task.status = 'in_progress'
        task.save()
        messages.success(request, f'Task "{task.title}" has been started!')
    return redirect('user_tasks')


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    context = {'task': task}
    return render(request, 'myapp/task_detail.html', context)


@login_required
def complete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    
    if request.method == 'POST':
        if task.status == 'in_progress':
            task.status = 'completed'
            task.save()
            messages.success(request, f'Task "{task.title}" has been completed!')
            return redirect('user_tasks')
    
    # If GET request, show confirmation page
    context = {'task': task}
    return render(request, 'myapp/task_confirm_complete.html', context)

@login_required
def verify_task(request, pk):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskVerificationForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.status = 'verified'
            task.save()
            
            # Award points to user
            user = task.assigned_to
            user.points += form.cleaned_data['points_awarded']
            user.save()
            
            return redirect('task_list')
    else:
        form = TaskVerificationForm(instance=task)
    
    return render(request, 'myapp/task_verify.html', {'form': form, 'task': task})


@login_required
def user_profile(request):
    # Initialize forms outside of POST check
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    
    if request.method == 'POST':
        if 'profile_form' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('user_profile')
        elif 'password_form' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password updated successfully!')
                return redirect('user_profile')

    # Calculate progress for level
    completed_count = request.user.assigned_tasks.filter(status='verified').count()
    current_level = request.user.rewards // 100
    next_level_points = (current_level + 1) * 100
    points_needed = max(0, next_level_points - request.user.points)
    progress = (request.user.points % 100) if current_level > 0 else request.user.points

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'completed_count': completed_count,
        'progress': progress,
        'points_needed': points_needed,
    }

    # Add role-specific data
    if request.user.is_admin:
        context.update({
            'user_count': CustomUser.objects.filter(is_admin=False).count(),
            'task_count': Task.objects.count(),
            'recent_tasks': Task.objects.order_by('-created_at')[:5],
            'is_admin': True
        })
    else:
        context.update({
            'points': request.user.points,
            'reward_level': f"Level {request.user.rewards // 100 + 1}",
            'is_admin': False
        })

    template = 'myapp/admin_profile.html' if request.user.is_admin else 'myapp/user_profile.html'
    return render(request, template, context)


def logout_view(request):
    logout(request)
    return redirect('login')