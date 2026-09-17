from django.contrib import admin

from .models import Enrollment, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('merchant_reference', 'user', 'course', 'amount', 'method', 'status', 'created_at')
    list_filter = ('status', 'method')
    search_fields = ('merchant_reference', 'user__username', 'user__phone')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'is_paid', 'expiry_date')
    list_filter = ('is_paid',)
