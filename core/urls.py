from django.urls import path

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.home, name='home'),
    path('manifest.json', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='service_worker'),
    path('offline/', views.offline_page, name='offline'),
    path('healthz/', views.healthz, name='healthz'),
    path('pricing/', views.info_page, {'slug': 'pricing'}, name='pricing'),
    path('payouts/', views.info_page, {'slug': 'payouts'}, name='payouts'),
    path('about/', views.info_page, {'slug': 'about'}, name='about'),
    path('trust/', views.info_page, {'slug': 'trust'}, name='trust'),
    path('terms/', views.info_page, {'slug': 'terms'}, name='terms'),
    path('privacy/', views.info_page, {'slug': 'privacy'}, name='privacy'),
]
