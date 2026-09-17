import uuid

from django.conf import settings
from django.db import models

from courses.models import Course


def generate_code():
    return uuid.uuid4().hex[:10].upper()


class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_code = models.CharField(max_length=20, unique=True, default=generate_code)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.certificate_code} - {self.user} - {self.course}'
