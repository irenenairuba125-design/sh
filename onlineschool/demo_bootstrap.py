"""Makes the site work on Vercel before a permanent DATABASE_URL is configured.

Without DATABASE_URL, Vercel runs on a temporary SQLite file in /tmp. That file starts
empty on every cold start, so create the tables and a few sample courses here. Accounts and
payments made in this mode are NOT kept; set DATABASE_URL for permanent data."""
import os


def ensure_demo_database():
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection

    if not os.environ.get('VERCEL') or connection.vendor != 'sqlite' or os.environ.get('DATABASE_URL'):
        return
    tables = connection.introspection.table_names()
    if 'core_sitesettings' not in tables or 'django_migrations' not in tables:
        call_command('migrate', interactive=False, verbosity=0)
    _seed()


def _seed():
    from accounts.models import User
    from core.models import SiteSettings
    from courses.models import Course, Lesson

    SiteSettings.load()
    if Course.objects.exists():
        return
    teacher = User(
        username='demo_lecturer', role=User.Role.TEACHER, is_verified_teacher=True,
        headline='Lecturer and practitioner', location='Kampala',
        bio='Practitioner who teaches the skills lecture halls skip.',
    )
    teacher.set_unusable_password()
    teacher.save()
    samples = [
        ('Start a small business with mobile money', 'business', 'beginner', 30000,
         'Pick an idea, price it, keep simple books and get your first customers.'),
        ('Excel for students and graduates', 'data', 'beginner', 20000,
         'Formulas, tables and charts you will actually use in coursework and at work.'),
        ('Python programming from zero', 'technology', 'beginner', 35000,
         'Write your first programs and build a small project step by step.'),
        ('Draft your first plaint in an afternoon', 'law', 'intermediate', 25000,
         'A walk through pleadings: parties, facts, causes of action and prayers.'),
        ('Write a CV that gets interviews', 'career', 'beginner', 10000,
         'Layout, wording and interview preparation for your first job.'),
    ]
    for title, category, level, price, description in samples:
        course = Course.objects.create(
            title=title, category=category, level=level, price=price, description=description,
            teacher=teacher, is_published=True,
        )
        Lesson.objects.create(course=course, title='Welcome and overview', kind=Lesson.Kind.VIDEO,
                              duration_minutes=5, order=1, free_preview=True)
