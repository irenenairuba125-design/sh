from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),
    path('payments/', include('payments.urls')),
    path('quizzes/', include('quizzes.urls')),
    path('certificates/', include('certificates.urls')),
    path('reviews/', include('reviews.urls')),
]

if settings.DEBUG:
    # Only public media (thumbnails, logos) lives under MEDIA_ROOT. Lesson videos and
    # notes live in PROTECTED_MEDIA_ROOT, which is intentionally never wired up here.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
