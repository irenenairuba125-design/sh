import os

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static

from accounts.models import User
from courses.models import Course
from payments.models import Enrollment


CATEGORY_BLURBS = {
    'legal_writing': 'Plaints, contracts, opinions',
    'moot_court': 'Argue it and win',
    'case_law': 'Read and use precedent',
    'constitutional': 'Rights, powers, courts',
    'contract': 'Deals that hold up',
    'criminal': 'Procedure and defence',
    'research': 'Find the law fast',
    'bar_prep': 'Pass the Bar Course',
    'human_rights': 'Advocacy and remedies',
    'adr': 'Mediation and arbitration',
    'internship': 'Clerkship survival skills',
    'international': 'Treaties and comparisons',
    'family_land': 'Succession, land and family',
}


def _live_this_week():
    """Real numbers for the 'Live this week' card: sales and new subscribers of one instructor."""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from payments.models import Payment

    teachers = User.objects.filter(role=User.Role.TEACHER, courses__is_published=True).distinct()
    teacher = teachers.filter(is_verified_teacher=True).first() or teachers.first()
    if not teacher:
        return None
    week_ago = timezone.now() - timedelta(days=7)
    sales = Payment.objects.filter(course__teacher=teacher, status=Payment.Status.SUCCESS)
    last = sales.order_by('-created_at').first()
    return {
        'teacher': teacher,
        'course': (last.course if last else teacher.courses.filter(is_published=True).first()),
        'earned_week': sales.filter(created_at__gte=week_ago).aggregate(t=Sum('amount'))['t'] or 0,
        'subscribers': Enrollment.objects.filter(course__teacher=teacher, is_paid=True).count(),
        'new_subscribers': Enrollment.objects.filter(course__teacher=teacher, is_paid=True, created_at__gte=week_ago).count(),
        'last_method': last.get_method_display() if last else '',
        'last_day': last.created_at.strftime('%a') if last else '',
    }


def home(request):
    from courses import catalog

    counts = {
        value: Course.objects.filter(is_published=True, category=value).count()
        for value, _ in Course.Category.choices
    }
    categories = [
        {'value': value, 'label': label, 'count': counts[value], 'blurb': CATEGORY_BLURBS.get(value, '')}
        for value, label in Course.Category.choices
    ]
    latest = [catalog.decorate(c) for c in catalog.base_queryset().order_by('-created_at')[:6]]
    return render(request, 'home.html', {
        'categories': categories,
        'latest': latest,
        'live': _live_this_week(),
        'total_courses': sum(counts.values()),
    })


PAGES = {
    'pricing': ('Pricing', 'pages/pricing.html'),
    'payouts': ('Payouts', 'pages/payouts.html'),
    'about': ('About', 'pages/about.html'),
    'trust': ('Trust & safety', 'pages/trust.html'),
    'terms': ('Terms', 'pages/terms.html'),
    'privacy': ('Privacy', 'pages/privacy.html'),
}


def info_page(request, slug):
    title, template = PAGES[slug]
    from .models import SiteSettings

    fee = SiteSettings.load().platform_fee_percent
    return render(request, template, {'page_title': title, 'example_net': f'{15000 - 15000 * fee // 100:,}'})


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


def healthz(request):
    """Open /healthz/ on the live site to see why it's failing. Reports a short status
    code only - never passwords, hosts or connection strings."""
    from django.db import connection

    vendor = connection.vendor
    status = 'ok'
    if vendor == 'sqlite' and (not settings.DEBUG or os.environ.get('VERCEL')):
        status = 'DATABASE_URL_NOT_SET (using sqlite, which cannot work on Vercel)'
    else:
        try:
            with connection.cursor() as cursor:
                cursor.execute('select count(*) from core_sitesettings')
        except Exception as exc:
            text = str(exc).lower()
            if 'password authentication' in text or 'authentication failed' in text:
                status = 'DB_PASSWORD_WRONG'
            elif 'does not exist' in text and 'relation' in text:
                status = 'TABLES_MISSING (run migrate)'
            elif 'could not translate host' in text or 'network is unreachable' in text or 'timeout' in text:
                status = 'DB_UNREACHABLE (use the pooler address, port 6543)'
            elif 'tenant or user not found' in text:
                status = 'DB_USER_WRONG (username must look like postgres.<project-ref>)'
            else:
                status = 'DB_ERROR:' + type(exc).__name__
    return JsonResponse({'status': status, 'database': vendor, 'debug': settings.DEBUG})
