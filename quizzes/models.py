from django.conf import settings
from django.db import models

from courses.models import Lesson


class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=200)
    pass_mark_percent = models.PositiveIntegerField(default=60)

    def __str__(self):
        return self.title


class Question(models.Model):
    CHOICES = [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    choice_a = models.CharField(max_length=255)
    choice_b = models.CharField(max_length=255)
    choice_c = models.CharField(max_length=255, blank=True)
    choice_d = models.CharField(max_length=255, blank=True)
    correct_choice = models.CharField(max_length=1, choices=CHOICES)

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score_percent = models.PositiveIntegerField()
    passed = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)
