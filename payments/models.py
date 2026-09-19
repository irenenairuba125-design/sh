from django.conf import settings
from django.db import models
from django.utils import timezone

from courses.models import Course


class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    is_paid = models.BooleanField(default=False)
    expiry_date = models.DateTimeField(null=True, blank=True, help_text='Blank = lifetime access')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def is_active(self):
        if not self.is_paid:
            return False
        if self.expiry_date and self.expiry_date < timezone.now():
            return False
        return True

    def __str__(self):
        return f'{self.user} - {self.course}'


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    class Method(models.TextChoices):
        MTN = 'mtn', 'MTN MoMo'
        AIRTEL = 'airtel', 'Airtel Money'
        CARD = 'card', 'Visa / Mastercard'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.OTHER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    merchant_reference = models.CharField(max_length=64, unique=True)
    pesapal_order_tracking_id = models.CharField(max_length=100, blank=True)
    momo_code = models.CharField(max_length=100, blank=True, help_text='Mobile-money transaction ID (or Pesapal confirmation code)')
    payer_phone = models.CharField(max_length=20, blank=True, help_text='Phone the student paid from (manual payments)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.merchant_reference} - {self.status}'
