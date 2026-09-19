from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import ProfileForm, RegisterForm
from .models import User


def register(request):
    wants_to_teach = request.GET.get('role') in ('creator', 'teacher')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        wants_to_teach = form.data.get('role') in ('creator', 'teacher')
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.TEACHER if form.cleaned_data['role'] == 'teacher' else User.Role.STUDENT
            if user.role == User.Role.TEACHER:
                for name in RegisterForm.TEACHER_FIELDS:
                    setattr(user, name, form.cleaned_data.get(name, ''))
            user.save()
            login(request, user)
            return redirect('accounts:post_login')
    else:
        form = RegisterForm(initial={'role': 'teacher' if wants_to_teach else 'student'})
    return render(request, 'accounts/register.html', {'form': form, 'wants_to_teach': wants_to_teach})


@login_required
def post_login_redirect(request):
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN:
        return redirect('courses:admin_dashboard')
    if user.role == User.Role.TEACHER:
        return redirect('courses:teacher_dashboard')
    return redirect('courses:my_learning')


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your details were saved.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@role_required('admin')
@require_POST
def verify_teacher(request, user_id):
    teacher = get_object_or_404(User, pk=user_id, role=User.Role.TEACHER)
    teacher.is_verified_teacher = not teacher.is_verified_teacher
    teacher.save(update_fields=['is_verified_teacher'])
    messages.success(request, '%s is now %s.' % (teacher.username, 'verified' if teacher.is_verified_teacher else 'unverified'))
    return redirect('courses:admin_dashboard')
