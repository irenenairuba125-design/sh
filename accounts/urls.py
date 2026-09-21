from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = 'accounts'
urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', redirect_authenticated_user=True, authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('after-login/', views.post_login_redirect, name='post_login'),
    path('me/', views.profile, name='profile'),
    path('verify/<int:user_id>/', views.verify_teacher, name='verify_teacher'),
]
