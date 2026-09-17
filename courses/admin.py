from django.contrib import admin

from .models import Course, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'teacher', 'price', 'access_days', 'is_published', 'created_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title',)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'free_preview')
    list_filter = ('free_preview',)
