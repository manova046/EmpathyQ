from django import forms
from django.contrib.auth import get_user_model
from .models import EmotionalCheckIn, Session, Progress

User = get_user_model()

class EmotionalCheckInForm(forms.ModelForm):
    class Meta:
        model = EmotionalCheckIn
        fields = ['emotion', 'intensity', 'notes']
        widgets = {
            'intensity': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '10', 'class': 'form-range'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'How are you feeling today?'}),
        }

class BookSessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['psychologist_name', 'session_type', 'scheduled_date', 'scheduled_time', 'notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any specific concerns or topics?'}),
        }

class ProgressForm(forms.ModelForm):
    class Meta:
        model = Progress
        fields = ['date', 'mood_score', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'mood_score': forms.NumberInput(attrs={'type': 'range', 'min': '1', 'max': '10', 'class': 'form-range'}),
        }

class ChatForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'}))