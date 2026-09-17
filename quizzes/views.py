from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from certificates.utils import issue_certificate_if_passed
from courses.views import _has_access
from .models import Quiz, QuizAttempt


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
