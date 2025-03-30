# myapp/forms.py
from django import forms
from .models import *

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'due_date', 'status', 'rating']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.is_admin:
            self.fields['assigned_to'].queryset = CustomUser.objects.filter(is_admin=False)
            # Make rating field optional for admins
            self.fields['rating'].required = False
            self.fields['rating'].widget = forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'step': 1
            })
        else:
            self.fields['assigned_to'].queryset = CustomUser.objects.none()
            if 'assigned_to' in self.fields:
                del self.fields['assigned_to']
            # Remove rating field for non-admins
            if 'rating' in self.fields:
                del self.fields['rating']

class TaskVerificationForm(forms.ModelForm):
    points_awarded = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=10,
        help_text="Points to award the user for completing this task"
    )
    
    class Meta:
        model = Task
        fields = ['rating', 'admin_notes', 'points_awarded']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }