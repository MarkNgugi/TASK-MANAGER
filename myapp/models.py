from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import FieldTracker

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    points = models.IntegerField(default=0)
    rewards = models.IntegerField(default=0)
    
    def __str__(self):
        return self.username

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_tasks')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assigned_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    admin_notes = models.TextField(null=True, blank=True)
    tracker = FieldTracker()  # For tracking field changes
    
    def __str__(self):
        return self.title

@receiver(post_save, sender=Task)
def update_user_points(sender, instance, created, **kwargs):
    if not created and instance.rating is not None:
        if instance.tracker.has_changed('rating'):
            old_rating = instance.tracker.previous('rating') or 0
            points_to_add = (instance.rating - old_rating) * 10
            if points_to_add > 0:
                instance.assigned_to.points += points_to_add
                instance.assigned_to.rewards += points_to_add
                instance.assigned_to.save()