from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TEACHER = 'teacher', 'Teacher'
        STUDENT = 'student', 'Student'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Phone number used for MTN MoMo / Airtel Money payments, e.g. 0771234567',
    )
    is_blocked = models.BooleanField(
        default=False,
        help_text='Blocked students cannot log in. Set this from /django-admin/.',
    )
    headline = models.CharField(
        max_length=120, blank=True,
        help_text='Shown on the homepage instructor spotlight, e.g. "Contracts that hold up"',
    )
    location = models.CharField(max_length=80, blank=True, help_text='e.g. "Kampala"')
    bio = models.TextField(blank=True, help_text='Short introduction shown on the instructor block')
    payout_phone = models.CharField(max_length=20, blank=True, help_text='Mobile-money number teachers are paid to')
    is_verified_teacher = models.BooleanField(
        default=False,
        help_text='Verified teachers can publish courses. Unverified teachers save drafts only.',
    )

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN
