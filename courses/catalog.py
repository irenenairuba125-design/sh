"""Everything the Browse page and the course cards need: ratings, subscriber counts,
lesson formats, badges and the filters. Numbers are computed from real data only."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Course

BESTSELLER_MIN_SUBSCRIBERS = 20
TRENDING_MIN_NEW_SUBSCRIBERS = 3
NEW_COURSE_DAYS = 14

PRICE_BANDS = {
    'under10k': ('Under UGX 10k', lambda p: p < 10000),
    '10to15k': ('UGX 10k – 15k', lambda p: 10000 <= p <= 15000),
    'over15k': ('Over UGX 15k', lambda p: p > 15000),
}
RATING_BANDS = {'4plus': ('4.0+', 4.0), '4half': ('4.5+', 4.5)}
FORMATS = {'video-heavy': 'Video-heavy', 'mixed': 'Mixed', 'audio-heavy': 'Audio-heavy'}
SORTS = {
    'newest': 'Newest',
    'popular': 'Most popular',
    'rating': 'Highest rated',
    'price_low': 'Price: low to high',
    'price_high': 'Price: high to low',
}


def base_queryset():
    return (
        Course.objects.filter(is_published=True)
        .select_related('teacher')
        .prefetch_related('lessons', 'reviews', 'enrollments')
    )


def decorate(course):
    """Attach computed display fields to a course (works on prefetched data)."""
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    ratings = [r.rating for r in course.reviews.all()]
    course.review_count = len(ratings)
    course.rating_avg = round(sum(ratings) / len(ratings), 1) if ratings else 0

    paid = [e for e in course.enrollments.all() if e.is_paid]
    course.subscribers = len(paid)
    new_subscribers = sum(1 for e in paid if e.created_at >= week_ago)

    lessons = list(course.lessons.all())
    course.lesson_list = lessons
    course.lesson_count = len(lessons)
    course.total_minutes = sum(l.duration_minutes for l in lessons)
    course.has_free_preview = any(l.free_preview for l in lessons)

    total = len(lessons) or 1
    video = sum(1 for l in lessons if l.kind == 'video') / total
    audio = sum(1 for l in lessons if l.kind == 'audio') / total
    if lessons and video >= 0.6:
        course.format_key = 'video-heavy'
    elif lessons and audio >= 0.4:
        course.format_key = 'audio-heavy'
    else:
        course.format_key = 'mixed'

    badges = []
    if course.subscribers >= BESTSELLER_MIN_SUBSCRIBERS:
        badges.append('Bestseller')
    if new_subscribers >= TRENDING_MIN_NEW_SUBSCRIBERS:
        badges.append('Trending')
    if course.created_at >= now - timedelta(days=NEW_COURSE_DAYS):
        badges.append('New')
    if course.has_free_preview:
        badges.append('Free preview')
    course.badges = badges
    course.price_period = '/month' if course.access_days == 30 else ''
    return course


def filtered_courses(params):
    """Apply the Browse page filters (query-string dict) and return (courses, active)."""
    qs = base_queryset()
    category = params.get('category', '')
    if category in dict(Course.Category.choices):
        qs = qs.filter(category=category)
    else:
        category = ''
    query = params.get('q', '').strip()[:100]
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(description__icontains=query)
            | Q(teacher__first_name__icontains=query) | Q(teacher__last_name__icontains=query)
            | Q(teacher__username__icontains=query)
        )

    courses = [decorate(c) for c in qs]

    price = params.get('price', '')
    if price in PRICE_BANDS:
        test = PRICE_BANDS[price][1]
        courses = [c for c in courses if test(c.price)]
    else:
        price = ''

    rating = params.get('rating', '')
    if rating in RATING_BANDS:
        minimum = RATING_BANDS[rating][1]
        courses = [c for c in courses if c.rating_avg >= minimum]
    else:
        rating = ''

    fmt = params.get('format', '')
    if fmt in FORMATS:
        courses = [c for c in courses if c.format_key == fmt]
    else:
        fmt = ''

    free_preview = params.get('freePreview') in ('true', '1', 'on')
    if free_preview:
        courses = [c for c in courses if c.has_free_preview]

    sort = params.get('sort', 'newest')
    if sort not in SORTS:
        sort = 'newest'
    if sort == 'popular':
        courses.sort(key=lambda c: (-c.subscribers, -c.created_at.timestamp()))
    elif sort == 'rating':
        courses.sort(key=lambda c: (-c.rating_avg, -c.review_count))
    elif sort == 'price_low':
        courses.sort(key=lambda c: c.price)
    elif sort == 'price_high':
        courses.sort(key=lambda c: -c.price)
    else:
        courses.sort(key=lambda c: -c.created_at.timestamp())

    active = {'category': category, 'q': query, 'price': price, 'rating': rating,
              'format': fmt, 'freePreview': free_preview, 'sort': sort}
    return courses, active
