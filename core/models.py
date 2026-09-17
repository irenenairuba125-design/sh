from django.db import models


class SiteSettings(models.Model):
    """Singleton row: the momo number, price defaults and logo an admin edits from /django-admin/."""

    site_name = models.CharField(max_length=100, default='Qiora for Law Students')
    tagline = models.CharField(
        max_length=200,
        blank=True,
        default='Learn the law skills lecture halls skip.',
    )
    momo_number = models.CharField(max_length=20, blank=True)
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    support_phone = models.CharField(max_length=20, blank=True)
    support_email = models.EmailField(blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.site_name
