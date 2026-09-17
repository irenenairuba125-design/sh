from django.contrib import admin

from .models import Question, Quiz, QuizAttempt


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'pass_mark_percent')
    inlines = [QuestionInline]


admin.site.register(QuizAttempt)
