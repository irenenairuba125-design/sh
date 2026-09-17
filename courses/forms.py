from django import forms

from .models import Course, Lesson


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'category', 'description', 'price', 'access_days', 'teacher', 'thumbnail', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'access_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'thumbnail': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'video_file', 'notes_pdf', 'free_preview']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'video_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes_pdf': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'free_preview': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
