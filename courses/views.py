import os
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from payments.models import Enrollment, Payment
from .forms import CourseForm, LessonForm
from .models import Course, Lesson

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
    course = get_object_or_404(Course, pk=pk, is_published=True)
    lessons = course.lessons.all()
    lessons_with_access = [(lesson, _has_access(request.user, lesson)) for lesson in lessons]

    enrollment = None
    is_paid = False
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        is_paid = bool(enrollment and enrollment.is_active())

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons_with_access': lessons_with_access,
        'is_paid': is_paid,
        'enrollment': enrollment,
    })


@login_required
def my_learning(request):
    enrollments = Enrollment.objects.filter(user=request.user, is_paid=True).select_related('course')
    certificates = request.user.certificates.select_related('course').all()
    return render(request, 'courses/my_learning.html', {
        'enrollments': enrollments,
        'certificates': certificates,
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
            course.save()
            messages.success(request, 'Course created. Now add its first lesson.')
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
            lesson.save()
            messages.success(request, 'Lesson uploaded.')
            return redirect('courses:upload_lesson', course_id=course.id)
    else:
        form = LessonForm()

    return render(request, 'courses/upload_lesson.html', {
        'form': form, 'course': course, 'lessons': course.lessons.all(),
    })


@role_required('teacher')
def teacher_dashboard(request):
    courses = Course.objects.filter(teacher=request.user)
    enrollments = Enrollment.objects.filter(course__in=courses, is_paid=True).select_related('user', 'course')
    return render(request, 'courses/teacher_dashboard.html', {
        'courses': courses,
        'enrollments': enrollments,
    })


@role_required('admin')
def admin_dashboard(request):
    total_courses = Course.objects.count()
    total_students = Enrollment.objects.filter(is_paid=True).values('user').distinct().count()
    total_revenue = sum(p.amount for p in Payment.objects.filter(status=Payment.Status.SUCCESS))
    pending_payments = Payment.objects.filter(status=Payment.Status.PENDING).count()
    return render(request, 'courses/admin_dashboard.html', {
        'total_courses': total_courses,
        'total_students': total_students,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'courses': Course.objects.all(),
    })
