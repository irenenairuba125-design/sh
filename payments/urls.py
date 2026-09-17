from django.urls import path

from . import views

app_name = 'payments'
urlpatterns = [
    path('checkout/<int:course_id>/', views.checkout, name='checkout'),
    path('callback/', views.payment_callback, name='callback'),
    path('ipn/', views.payment_ipn, name='ipn'),
    path('admin/', views.admin_payments, name='admin_payments'),
    path('admin/<int:payment_id>/approve/', views.approve_payment, name='approve_payment'),
]
