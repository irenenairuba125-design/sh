from django.shortcuts import render

from accounts.models import User
from courses.models import Course
from payments.models import Enrollment


def home(request):
    courses = Course.objects.filter(is_published=True)

    selected_category = request.GET.get('category', '')
    if selected_category:
        courses = courses.filter(category=selected_category)
    courses = courses.order_by('-created_at')

    category_counts = [
        {'value': value, 'label': label, 'count': Course.objects.filter(is_published=True, category=value).count()}
        for value, label in Course.Category.choices
    ]

    spotlight = None
    spotlight_teacher = (
        User.objects.filter(role=User.Role.TEACHER, courses__is_published=True).distinct().first()
    )
    if spotlight_teacher:
        spotlight = {
            'teacher': spotlight_teacher,
            'course': spotlight_teacher.courses.filter(is_published=True).first(),
            'subscribers': Enrollment.objects.filter(course__teacher=spotlight_teacher, is_paid=True).count(),
        }

    return render(request, 'home.html', {
        'courses': courses,
        'category_counts': category_counts,
        'selected_category': selected_category,
        'spotlight': spotlight,
    })
