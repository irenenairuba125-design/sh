from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from courses.models import Course
from payments.models import Enrollment
from .models import Review


@login_required
def add_review(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    enrolled = Enrollment.objects.filter(user=request.user, course=course, is_paid=True).exists()
    if not enrolled:
        messages.error(request, 'Only students who paid for this course can leave a review.')
        return redirect('courses:course_detail', pk=course.id)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        Review.objects.update_or_create(
            user=request.user, course=course, defaults={'rating': rating, 'comment': comment},
        )
        messages.success(request, 'Thanks for your review!')

    return redirect('courses:course_detail', pk=course.id)
