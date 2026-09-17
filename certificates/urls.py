from django.urls import path

from . import views

app_name = 'certificates'
urlpatterns = [
    path('verify/<str:code>/', views.verify_certificate, name='verify'),
]
