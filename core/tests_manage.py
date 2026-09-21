from django.urls import reverse

from courses.models import Course, Lesson
from payments.models import Enrollment
from quizzes.models import Question, Quiz, QuizAttempt

from .tests import Base


class CourseManagement(Base):
    def test_teacher_can_edit_own_course_not_others(self):
        url = reverse('courses:edit_course', args=[self.course.id])
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {'title': 'Renamed', 'category': 'law', 'level': 'beginner', 'description': 'x',
                                   'price': '45000', 'is_published': 'on'})
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual((self.course.title, int(self.course.price), self.course.teacher), ('Renamed', 45000, self.teacher))

    def test_admin_can_reassign_teacher(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('courses:edit_course', args=[self.course.id]), {
            'title': 'T', 'category': 'law', 'level': 'beginner', 'description': '', 'price': '1000',
            'teacher': self.other_teacher.id, 'is_published': 'on'})
        self.assertEqual(r.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.teacher, self.other_teacher)

    def test_delete_needs_post_and_ownership(self):
        url = reverse('courses:delete_course', args=[self.course.id])
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(Course.objects.filter(pk=self.course.id).count(), 1)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Course.objects.filter(pk=self.course.id).exists())

    def test_delete_lesson(self):
        url = reverse('courses:delete_lesson', args=[self.paid_lesson.id])
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Lesson.objects.filter(pk=self.paid_lesson.id).exists())

    def test_upload_without_disk_fails_gracefully(self):
        from unittest import mock
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.teacher)
        with mock.patch('courses.models.Lesson.save', side_effect=OSError(30, 'Read-only file system')):
            r = self.client.post(reverse('courses:upload_lesson', args=[self.course.id]), {
                'title': 'V', 'kind': 'video', 'duration_minutes': 5, 'order': 3, 'video_file': SimpleUploadedFile('v.mp4', b'123')})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no permanent disk')

    def test_teacher_dashboard_shows_quiz_results(self):
        quiz = Quiz.objects.create(lesson=self.paid_lesson, title='Lesson quiz')
        Question.objects.create(quiz=quiz, text='q', choice_a='a', choice_b='b', correct_choice='a')
        QuizAttempt.objects.create(user=self.student, quiz=quiz, score_percent=80, passed=True)
        self.client.force_login(self.teacher)
        r = self.client.get(reverse('courses:teacher_dashboard'))
        self.assertContains(r, 'Recent quiz results')
        self.assertContains(r, '80%')
        self.client.force_login(self.other_teacher)
        self.assertNotContains(self.client.get(reverse('courses:teacher_dashboard')), '80%')


class Search(Base):
    def test_search_filters_courses(self):
        Course.objects.create(title='Moot Court Mastery', description='advocacy skills', price=1, teacher=self.teacher)
        html = self.client.get('/courses/', {'q': 'moot'}).content.decode()
        self.assertIn('Moot Court Mastery', html)
        self.assertNotIn('Zebra Plaint Basics', html)
        self.assertIn('No courses match', self.client.get('/courses/', {'q': 'zzzzqqqq'}).content.decode())
        self.assertEqual(self.client.get('/courses/', {'q': 'x' * 500}).status_code, 200)

    def test_search_combines_with_category(self):
        html = self.client.get('/courses/', {'q': 'zebra', 'category': 'law'}).content.decode()
        self.assertIn('No courses match', html)
        html = self.client.get('/courses/', {'q': 'zebra', 'category': 'business'}).content.decode()
        self.assertNotIn('No courses match', html)


class CertificatePage(Base):
    def test_certificate_has_print_button(self):
        from certificates.models import Certificate
        cert = Certificate.objects.create(user=self.student, course=self.course)
        r = self.client.get(reverse('certificates:verify', args=[cert.certificate_code]))
        self.assertContains(r, 'window.print()')
        self.assertContains(r, self.course.title)
