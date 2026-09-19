import os
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from payments.models import Enrollment, Payment
from quizzes.models import QuizAttempt
from .forms import CourseForm, LessonForm
from .models import Course, Lesson

STORAGE_UNAVAILABLE = (
    "This server has no permanent disk, so files (videos, notes, thumbnails) cannot be saved here. "
    "Upload files from a server with storage, or connect cloud file storage."
)

DRAFT_NOTICE = (
    'Saved as a draft. Your course goes live once an admin verifies your instructor account.'
)

RANGE_RE = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.IGNORECASE)


def _has_access(user, lesson):
    """The single gate every locked-content view goes through. Free previews are open
    to everyone; otherwise you need to be the course's teacher, an admin/superuser, or
    have a paid, non-expired enrollment."""
    is_staff_user = user.is_authenticated and (
        user.is_superuser
        or getattr(user, 'role', None) == 'admin'
        or (getattr(user, 'role', None) == 'teacher' and lesson.course.teacher_id == user.id)
    )
    if is_staff_user:
        return True
    if not lesson.course.is_published:
        return False
    if lesson.free_preview:
        return True
    if not user.is_authenticated:
        return False
    enrollment = Enrollment.objects.filter(user=user, course=lesson.course).first()
    return bool(enrollment and enrollment.is_active())


def course_detail(request, pk):
    from . import catalog

    course = get_object_or_404(
        Course.objects.select_related('teacher').prefetch_related('lessons', 'reviews', 'enrollments'),
        pk=pk, is_published=True,
    )
    catalog.decorate(course)
    lessons_with_access = [(lesson, _has_access(request.user, lesson)) for lesson in course.lesson_list]

    modules = []
    for lesson, has_access in lessons_with_access:
        title = lesson.module_title or 'Lessons'
        if not modules or modules[-1]['title'] != title:
            modules.append({'title': title, 'items': [], 'minutes': 0})
        modules[-1]['items'].append((lesson, has_access))
        modules[-1]['minutes'] += lesson.duration_minutes

    teacher = course.teacher
    teacher_stats = None
    if teacher:
        teacher_stats = {
            'courses': Course.objects.filter(teacher=teacher, is_published=True).count(),
            'subscribers': Enrollment.objects.filter(course__teacher=teacher, is_paid=True).count(),
        }
    reviews = course.reviews.select_related('user').order_by('-created_at')[:10]

    enrollment = None
    is_paid = False
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        is_paid = bool(enrollment and enrollment.is_active())

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons_with_access': lessons_with_access,
        'modules': modules,
        'teacher_stats': teacher_stats,
        'reviews': reviews,
        'is_paid': is_paid,
        'enrollment': enrollment,
    })


@login_required
def my_learning(request):
    enrollments = Enrollment.objects.filter(user=request.user, is_paid=True).select_related('course')
    certificates = request.user.certificates.select_related('course').all()
    pending = Payment.objects.filter(user=request.user, status=Payment.Status.PENDING).exclude(momo_code='').select_related('course')
    return render(request, 'courses/my_learning.html', {
        'enrollments': enrollments,
        'certificates': certificates,
        'pending': pending,
    })


def watch_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if not _has_access(request.user, lesson):
        messages.error(request, 'Pay for this course to watch this lesson.')
        return redirect('courses:course_detail', pk=lesson.course_id)
    return render(request, 'courses/video_player.html', {'lesson': lesson})


def stream_video(request, lesson_id):
    """Streams the lesson video byte-range by byte-range, after checking access on every
    request. There is no public URL to the file itself (it lives outside MEDIA_ROOT in
    PROTECTED_MEDIA_ROOT) - this view is the only door, so a student who hasn't paid
    can't just grab and share a direct link."""
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if not lesson.video_file:
        raise Http404
    if not _has_access(request.user, lesson):
        return HttpResponseForbidden("You need to pay for this course to watch this lesson.")

    path = lesson.video_file.path
    file_size = os.path.getsize(path)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = RANGE_RE.match(range_header) if range_header else None
    content_type = 'video/mp4'

    def file_iterator(start, length, chunk_size=8192):
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1
        response = StreamingHttpResponse(file_iterator(start, length), status=206, content_type=content_type)
        response['Content-Length'] = str(length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    else:
        response = StreamingHttpResponse(file_iterator(0, file_size), content_type=content_type)
        response['Content-Length'] = str(file_size)

    response['Accept-Ranges'] = 'bytes'
    response['Content-Disposition'] = 'inline; filename="lesson.mp4"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def download_notes(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if not lesson.notes_pdf:
        raise Http404
    if not _has_access(request.user, lesson):
        return HttpResponseForbidden("You need to pay for this course to download these notes.")
    return FileResponse(
        open(lesson.notes_pdf.path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(lesson.notes_pdf.name),
    )


@role_required('admin', 'teacher')
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if request.user.role == 'teacher':
            form.fields.pop('teacher', None)
        if form.is_valid():
            course = form.save(commit=False)
            if request.user.role == 'teacher':
                course.teacher = request.user
            draft = _force_draft(request.user, course)
            try:
                course.save()
            except OSError:
                messages.error(request, STORAGE_UNAVAILABLE)
            else:
                messages.success(request, DRAFT_NOTICE if draft else 'Course created. Now add its first lesson.')
                return redirect('courses:upload_lesson', course_id=course.id)
    else:
        form = CourseForm()
        if request.user.role == 'teacher':
            form.fields.pop('teacher', None)
    return render(request, 'courses/add_course.html', {'form': form})


@role_required('admin', 'teacher')
def upload_lesson(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if request.user.role == 'teacher' and course.teacher_id != request.user.id:
        return HttpResponseForbidden("You don't own this course.")

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            try:
                lesson.save()
            except OSError:
                messages.error(request, STORAGE_UNAVAILABLE)
            else:
                messages.success(request, 'Lesson uploaded.')
                return redirect('courses:upload_lesson', course_id=course.id)
    else:
        form = LessonForm()

    return render(request, 'courses/upload_lesson.html', {
        'form': form, 'course': course, 'lessons': course.lessons.all(),
    })


def _force_draft(user, course):
    """Unverified teachers can only save drafts; returns True when it was forced."""
    if _is_plain_teacher(user) and not user.is_verified_teacher and course.is_published:
        course.is_published = False
        return True
    return False


@role_required('teacher')
def teacher_dashboard(request):
    courses = Course.objects.filter(teacher=request.user)
    enrollments = Enrollment.objects.filter(course__in=courses, is_paid=True).select_related('user', 'course')
    attempts = (
        QuizAttempt.objects.filter(quiz__lesson__course__in=courses)
        .select_related('user', 'quiz__lesson__course').order_by('-attempted_at')[:25]
    )
    from payments.earnings import teacher_earnings
    from payments.models import Payout

    return render(request, 'courses/teacher_dashboard.html', {
        'courses': courses,
        'enrollments': enrollments,
        'attempts': attempts,
        'earnings': teacher_earnings(request.user),
        'payouts': Payout.objects.filter(teacher=request.user)[:10],
    })


@role_required('admin')
def admin_dashboard(request):
    total_courses = Course.objects.count()
    total_students = Enrollment.objects.filter(is_paid=True).values('user').distinct().count()
    total_revenue = sum(p.amount for p in Payment.objects.filter(status=Payment.Status.SUCCESS))
    pending_payments = Payment.objects.filter(status=Payment.Status.PENDING).count()
    from accounts.models import User

    return render(request, 'courses/admin_dashboard.html', {
        'teachers': User.objects.filter(role=User.Role.TEACHER).order_by('is_verified_teacher', 'username'),
        'total_courses': total_courses,
        'total_students': total_students,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'courses': Course.objects.all(),
    })


def _is_plain_teacher(user):
    return user.role == 'teacher' and not user.is_superuser


@role_required('admin', 'teacher')
def edit_course(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if _is_plain_teacher(request.user) and course.teacher_id != request.user.id:
        return HttpResponseForbidden("You do not own this course.")

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if _is_plain_teacher(request.user):
            form.fields.pop('teacher', None)
        if form.is_valid():
            edited = form.save(commit=False)
            draft = _force_draft(request.user, edited)
            try:
                edited.save()
            except OSError:
                messages.error(request, STORAGE_UNAVAILABLE)
            else:
                messages.success(request, DRAFT_NOTICE if draft else 'Course updated.')
                return redirect('courses:upload_lesson', course_id=course.id)
    else:
        form = CourseForm(instance=course)
        if _is_plain_teacher(request.user):
            form.fields.pop('teacher', None)
    return render(request, 'courses/add_course.html', {'form': form, 'editing': course})


@role_required('admin', 'teacher')
@require_POST
def delete_course(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if _is_plain_teacher(request.user) and course.teacher_id != request.user.id:
        return HttpResponseForbidden("You do not own this course.")
    title = course.title
    course.delete()
    messages.success(request, 'Deleted "%s".' % title)
    return redirect('courses:teacher_dashboard' if _is_plain_teacher(request.user) else 'courses:admin_dashboard')


@role_required('admin', 'teacher')
@require_POST
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if _is_plain_teacher(request.user) and lesson.course.teacher_id != request.user.id:
        return HttpResponseForbidden("You do not own this course.")
    course_id = lesson.course_id
    lesson.delete()
    messages.success(request, 'Lesson deleted.')
    return redirect('courses:upload_lesson', course_id=course_id)


def browse(request):
    from django.db.models import Count
    from . import catalog

    courses, active = catalog.filtered_courses(request.GET)
    counts = dict(
        Course.objects.filter(is_published=True).values_list('category').annotate(n=Count('id'))
    )
    categories = [
        {'value': value, 'label': label, 'count': counts.get(value, 0)}
        for value, label in Course.Category.choices
    ]
    return render(request, 'courses/browse.html', {
        'courses': courses,
        'active': active,
        'categories': categories,
        'price_bands': [(k, v[0]) for k, v in catalog.PRICE_BANDS.items()],
        'rating_bands': [(k, v[0]) for k, v in catalog.RATING_BANDS.items()],
        'formats': list(catalog.FORMATS.items()),
        'sorts': list(catalog.SORTS.items()),
        'any_filter': any([active['category'], active['q'], active['price'], active['rating'],
                           active['format'], active['freePreview']]),
    })
