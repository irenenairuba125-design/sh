from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from certificates.utils import issue_certificate_if_passed
from courses.models import Lesson
from courses.views import _has_access
from .forms import QuestionForm, QuizForm
from .models import Question, Quiz, QuizAttempt


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    lesson = quiz.lesson
    if not _has_access(request.user, lesson):
        messages.error(request, 'Pay for this course to take the quiz.')
        return redirect('courses:course_detail', pk=lesson.course_id)

    questions = quiz.questions.all()

    if request.method == 'POST':
        correct = 0
        for q in questions:
            if request.POST.get(f'q{q.id}') == q.correct_choice:
                correct += 1
        total = questions.count()
        score_percent = round((correct / total) * 100) if total else 0
        passed = score_percent >= quiz.pass_mark_percent

        attempt = QuizAttempt.objects.create(
            user=request.user, quiz=quiz, score_percent=score_percent, passed=passed,
        )
        certificate = issue_certificate_if_passed(request.user, lesson.course) if passed else None
        return render(request, 'quizzes/result.html', {
            'attempt': attempt, 'quiz': quiz, 'certificate': certificate,
        })

    return render(request, 'quizzes/quiz.html', {'quiz': quiz, 'questions': questions})


@role_required('admin', 'teacher')
def manage_quiz(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if request.user.role == 'teacher' and lesson.course.teacher_id != request.user.id:
        return HttpResponseForbidden("You don't own this course.")

    quiz = Quiz.objects.filter(lesson=lesson).first()
    quiz_form = QuizForm(instance=quiz)
    question_form = QuestionForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'quiz':
            quiz_form = QuizForm(request.POST, instance=quiz)
            if quiz_form.is_valid():
                saved = quiz_form.save(commit=False)
                saved.lesson = lesson
                saved.save()
                messages.success(request, 'Quiz saved.')
                return redirect('quizzes:manage', lesson_id=lesson.id)
        elif action == 'question' and quiz:
            question_form = QuestionForm(request.POST)
            if question_form.is_valid():
                question = question_form.save(commit=False)
                question.quiz = quiz
                question.save()
                messages.success(request, 'Question added.')
                return redirect('quizzes:manage', lesson_id=lesson.id)
        elif action == 'delete_question' and quiz:
            Question.objects.filter(pk=request.POST.get('question_id'), quiz=quiz).delete()
            return redirect('quizzes:manage', lesson_id=lesson.id)

    return render(request, 'quizzes/manage_quiz.html', {
        'lesson': lesson, 'quiz': quiz, 'quiz_form': quiz_form, 'question_form': question_form,
        'questions': quiz.questions.all() if quiz else [],
    })
