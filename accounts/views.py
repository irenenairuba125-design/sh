from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegisterForm
from .models import User


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.STUDENT
            user.save()
            login(request, user)
            return redirect('accounts:post_login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def post_login_redirect(request):
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN:
        return redirect('courses:admin_dashboard')
    if user.role == User.Role.TEACHER:
        return redirect('courses:teacher_dashboard')
    return redirect('courses:my_learning')
