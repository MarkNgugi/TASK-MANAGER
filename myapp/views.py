from django.shortcuts import redirect,render,get_object_or_404
from django.contrib.auth import login, authenticate
from django.db.models import Count, Q, Avg 
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import *

class CustomLoginView(LoginView):
    template_name = 'myapp/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_superuser or user.is_admin:
                return reverse_lazy('admin_dashboard')
        return reverse_lazy('user_dashboard')

@login_required
def redirect_view(request):
    if request.user.is_superuser or request.user.is_admin:
        return redirect('admin_dashboard')
    return redirect('user_dashboard')

# Keep only ONE version of each dashboard view (the detailed ones):

@login_required
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect('user_dashboard')
    
    # Get all stats
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='pending').count()
    active_users = CustomUser.objects.filter(is_admin=False).count()
    completed_tasks = Task.objects.filter(status='verified').count()
    
    # Get top performers with their verified task counts
    top_performers = CustomUser.objects.filter(is_admin=False).annotate(
        verified_count=Count('assigned_tasks', filter=Q(assigned_tasks__status='verified'))
    ).order_by('-points')[:5]
    
    recent_activities = [
        "User 'johndoe' completed task 'Update website content'",
        "You assigned a new task to 'janedoe'",
        "User 'mikesmith' reached 100 points",
        "You rated task 'Fix login issue' with 4 stars"
    ][:5]
    
    context = {
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
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
    pending_count = user.assigned_tasks.filter(status='pending').count()
    in_progress_count = user.assigned_tasks.filter(status='in_progress').count()
    completed_count = user.assigned_tasks.filter(status__in=['completed', 'verified']).count()
    
    # Calculate progress to next reward level
    points_needed = max(0, (user.points // 100 + 1) * 100 - user.points)
    progress = min(100, (user.points % 100))
    
    # Get reward level
    reward_level = f"Level {user.points // 100 + 1}"
    rewards_available = user.rewards
    
    # Get top performers
    top_performers = CustomUser.objects.filter(is_admin=False)\
        .annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status='verified')),
            average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
        )\
        .order_by('-points')[:10]
    
    # Find user's position
    user_position = None
    for i, performer in enumerate(top_performers, 1):
        if performer == user:
            user_position = i
            break
    
    # Sample recent activities
    recent_activities = [
        {'title': 'Task "Update profile" marked as completed', 'date': '2 hours ago', 'icon': 'fas fa-check-circle'},
        {'title': 'Received 10 points for "Fix bugs"', 'date': '1 day ago', 'icon': 'fas fa-coins'},
        {'title': 'Task "Write documentation" assigned', 'date': '3 days ago', 'icon': 'fas fa-tasks'},
    ]
    
    context = {
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'progress': progress,
        'points_needed': points_needed,
        'reward_level': reward_level,
        'rewards_available': rewards_available,
        'top_performers': top_performers,
        'user_position': user_position,
        'user_completed': completed_count,
        'user_rating': 4,
        'recent_activities': recent_activities,
    }
    return render(request, 'myapp/user_dashboard.html', context)

def manage_tasks(request):
    context={}
    return render(request,'myapp/manage_tasks.html',context)


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
            task.save()
            return redirect('task_list')
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
            form.save()
            return redirect('task_list')
    else:
        form = TaskForm(instance=task, user=request.user)
    
    context = {
        'form': form,
        'task': task
    }
    return render(request, 'myapp/task_form.html', context)

@login_required
def leaderboard(request):
    users = CustomUser.objects.filter(is_admin=False)\
        .annotate(
            completed_tasks=Count('assigned_tasks', filter=Q(assigned_tasks__status='verified')),
            average_rating=Avg('assigned_tasks__rating', filter=Q(assigned_tasks__rating__isnull=False))
        )\
        .order_by('-points')
    
    context = {
        'users': users,
        'is_admin': request.user.is_admin,
    }
    return render(request, 'myapp/leaderboard.html', context)

@login_required
def complete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, assigned_to=request.user)
    if request.method == 'POST':
        task.status = 'completed'
        task.save()
        return redirect('my_tasks')
    return render(request, 'myapp/task_confirm_complete.html', {'task': task})

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