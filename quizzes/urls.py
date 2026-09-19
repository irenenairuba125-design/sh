from django.urls import path

from . import views

app_name = 'quizzes'
urlpatterns = [
    path('<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('lesson/<int:lesson_id>/manage/', views.manage_quiz, name='manage'),
]
