from django import forms

from .models import Question, Quiz


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'pass_mark_percent']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'pass_mark_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
        }

    def clean_pass_mark_percent(self):
        value = self.cleaned_data['pass_mark_percent']
        if not 1 <= value <= 100:
            raise forms.ValidationError('Pass mark must be between 1 and 100.')
        return value


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'choice_a', 'choice_b', 'choice_c', 'choice_d', 'correct_choice']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'choice_a': forms.TextInput(attrs={'class': 'form-control'}),
            'choice_b': forms.TextInput(attrs={'class': 'form-control'}),
            'choice_c': forms.TextInput(attrs={'class': 'form-control'}),
            'choice_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_choice': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        data = super().clean()
        correct = data.get('correct_choice')
        if correct and not data.get(f'choice_{correct}'):
            raise forms.ValidationError('The correct answer must be one of the filled-in choices.')
        return data
