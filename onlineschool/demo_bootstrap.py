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
        username='demo_advocate', role=User.Role.TEACHER, is_verified_teacher=True,
        headline='Advocate of the High Court', location='Kampala',
        bio='Practising advocate who teaches the skills lecture halls skip.',
    )
    teacher.set_unusable_password()
    teacher.save()
    samples = [
        ('Draft your first plaint in an afternoon', 'legal_writing', 'beginner', 30000,
         'A step-by-step walk through pleadings: parties, facts, causes of action and prayers.'),
        ('Moot court: argue it and win', 'moot_court', 'intermediate', 25000,
         'Structure a submission, handle judges\' questions and rebut like a practising advocate.'),
        ('Case briefing that saves hours', 'case_law', 'beginner', 15000,
         'Read a judgment quickly, pull out the ratio and build a brief you can reuse.'),
        ('Pass the Bar Course', 'bar_prep', 'advanced', 45000,
         'Study plans, past-paper practice and exam technique for the Law Development Centre.'),
    ]
    for title, category, level, price, description in samples:
        course = Course.objects.create(
            title=title, category=category, level=level, price=price, description=description,
            teacher=teacher, is_published=True,
        )
        Lesson.objects.create(course=course, title='Welcome and overview', kind=Lesson.Kind.VIDEO,
                              duration_minutes=5, order=1, free_preview=True)
