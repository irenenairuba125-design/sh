from django.urls import path

from . import views

app_name = 'courses'
urlpatterns = [
    path('my-learning/', views.my_learning, name='my_learning'),
    path('teach/add/', views.add_course, name='add_course'),
    path('teach/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teach/<int:course_id>/upload-lesson/', views.upload_lesson, name='upload_lesson'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('lesson/<int:lesson_id>/watch/', views.watch_lesson, name='watch_lesson'),
    path('lesson/<int:lesson_id>/stream/', views.stream_video, name='stream_video'),
    path('lesson/<int:lesson_id>/notes/', views.download_notes, name='download_notes'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
]
