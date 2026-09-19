import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static

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


def manifest(request):
    """The web app manifest that lets a phone browser install this site as an app
    ("Add to Home Screen" on Android, "Add to Home Screen" from the Share sheet on
    iOS). Generated in code rather than a static file so the name always matches
    SiteSettings if you customise it later."""
    data = {
        'name': 'Qiora for Law Students',
        'short_name': 'Qiora',
        'description': "Practical legal skills for law students — moot court, drafting, case briefing and Bar Course prep.",
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#F6F8F9',
        'theme_color': '#0FA898',
        'orientation': 'portrait-primary',
        'icons': [
            {'src': static('core/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('core/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('core/icon-512-maskable.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return JsonResponse(data, content_type='application/manifest+json')


def service_worker(request):
    """Served at /sw.js (not /static/sw.js) so its default scope is the whole site."""
    path = os.path.join(settings.BASE_DIR, 'core', 'pwa_sw.js')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


def offline_page(request):
    return render(request, 'offline.html')
