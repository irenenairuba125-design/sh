from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from onlineschool.storage_backends import protected_storage


class Course(models.Model):
    class Category(models.TextChoices):
        LEGAL_WRITING = 'legal_writing', 'Legal Writing & Drafting'
        MOOT_COURT = 'moot_court', 'Moot Court & Advocacy'
        CASE_LAW = 'case_law', 'Case Law & Precedent'
        CONSTITUTIONAL = 'constitutional', 'Constitutional Law'
        CONTRACT = 'contract', 'Contract & Commercial Law'
        CRIMINAL = 'criminal', 'Criminal Law & Procedure'
        RESEARCH = 'research', 'Legal Research Methods'
        BAR_PREP = 'bar_prep', 'Bar Course Prep'
        HUMAN_RIGHTS = 'human_rights', 'Human Rights Law'
        ADR = 'adr', 'Alternative Dispute Resolution'
        INTERNSHIP = 'internship', 'Internship & Clerkship Skills'
        INTERNATIONAL = 'international', 'International & Comparative Law'
        FAMILY_LAND = 'family_land', 'Family & Land Law'

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=0, validators=[MinValueValidator(0)],
        help_text='Price in UGX, e.g. 30000',
    )
    access_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Leave blank for lifetime access once paid. Set 30 for "monthly access", 90 for "full term".',
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'role': 'teacher'}, related_name='courses',
    )
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(models.Avg('rating'))
        return agg['rating__avg'] or 0


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    video_file = models.FileField(upload_to='videos/', storage=protected_storage, blank=True, null=True)
    notes_pdf = models.FileField(upload_to='notes/', storage=protected_storage, blank=True, null=True)
    free_preview = models.BooleanField(
        default=False,
        help_text='Anyone can watch this lesson without paying (use for one marketing preview per course).',
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course.title} - {self.title}'
