import os
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from certificates.models import Certificate
from courses.models import Course, Lesson
from payments.models import Enrollment, Payment
from quizzes.models import Question, Quiz, QuizAttempt
from reviews.models import Review

TMP_PROTECTED = tempfile.mkdtemp()


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('boss', 'b@x.com', 'pw12345!x')
        cls.teacher = User.objects.create_user('teach', 't@x.com', 'pw12345!x', role='teacher', phone='0771')
        cls.other_teacher = User.objects.create_user('teach2', 't2@x.com', 'pw12345!x', role='teacher')
        cls.student = User.objects.create_user('stud', 's@x.com', 'pw12345!x', phone='0772')
        cls.course = Course.objects.create(title='Zebra Plaint Basics', price=30000, teacher=cls.teacher, category='legal_writing')
        cls.free_lesson = Lesson.objects.create(course=cls.course, title='Free', order=1, free_preview=True)
        cls.paid_lesson = Lesson.objects.create(course=cls.course, title='Paid', order=2)


class PublicPages(Base):
    def test_pages_load(self):
        for name in ['core:home', 'accounts:login', 'accounts:register', 'core:manifest', 'core:service_worker', 'core:offline']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse('courses:course_detail', args=[self.course.id])).status_code, 200)
        self.assertEqual(self.client.get('/?category=nonsense').status_code, 200)

    def test_unpublished_course_hidden(self):
        self.course.is_published = False
        self.course.save()
        self.assertEqual(self.client.get(reverse('courses:course_detail', args=[self.course.id])).status_code, 404)
        self.assertNotContains(self.client.get('/'), 'Zebra Plaint Basics')

    def test_register_creates_student_not_admin(self):
        r = self.client.post(reverse('accounts:register'), {
            'username': 'newbie', 'email': 'n@x.com', 'phone': '0773',
            'password1': 'Str0ng-pass-99', 'password2': 'Str0ng-pass-99', 'role': 'admin',
        })
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username='newbie')
        self.assertEqual(u.role, 'student')
        self.assertFalse(u.is_superuser)

    def test_logout_works_via_post(self):
        self.client.force_login(self.student)
        r = self.client.post(reverse('accounts:logout'))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_nav_logout_is_a_post_form(self):
        self.client.force_login(self.student)
        html = self.client.get('/').content.decode()
        self.assertIn('action="%s"' % reverse('accounts:logout'), html)


class Paywall(Base):
    def test_free_preview_open_to_anonymous_locked_is_not(self):
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.free_lesson.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 302)

    def test_unpaid_student_locked_paid_student_open(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 302)
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 200)

    def test_expired_enrollment_locks_again(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True,
                                  expiry_date=timezone.now() - timedelta(days=1))
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 302)

    def test_other_teacher_cannot_watch_but_owner_can(self):
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 302)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 200)

    def test_unpublished_course_lessons_not_watchable_by_students(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        self.course.is_published = False
        self.course.save()
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('courses:watch_lesson', args=[self.paid_lesson.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse('courses:stream_video', args=[self.paid_lesson.id])).status_code, 404)


@override_settings(PROTECTED_MEDIA_ROOT=TMP_PROTECTED)
class Streaming(Base):
    def setUp(self):
        from django.core.files.storage import FileSystemStorage
        storage = FileSystemStorage(location=TMP_PROTECTED)
        field = Lesson._meta.get_field('video_file')
        notes = Lesson._meta.get_field('notes_pdf')
        self._old = (field.storage, notes.storage)
        field.storage = storage
        notes.storage = storage
        self.data = bytes(range(256)) * 40
        self.paid_lesson.video_file.save('v.mp4', SimpleUploadedFile('v.mp4', self.data), save=True)
        self.paid_lesson.notes_pdf.save('n.pdf', SimpleUploadedFile('n.pdf', b'%PDF-1.4 notes'), save=True)

    def tearDown(self):
        Lesson._meta.get_field('video_file').storage, Lesson._meta.get_field('notes_pdf').storage = self._old

    def test_stream_blocked_when_unpaid_and_full_when_paid(self):
        url = reverse('courses:stream_video', args=[self.paid_lesson.id])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), self.data)

    def test_range_requests(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        self.client.force_login(self.student)
        url = reverse('courses:stream_video', args=[self.paid_lesson.id])
        r = self.client.get(url, HTTP_RANGE='bytes=10-19')
        self.assertEqual(r.status_code, 206)
        self.assertEqual(b''.join(r.streaming_content), self.data[10:20])
        self.assertEqual(r['Content-Range'], 'bytes 10-19/%d' % len(self.data))
        r = self.client.get(url, HTTP_RANGE='bytes=%d-' % (len(self.data) - 5))
        self.assertEqual(b''.join(r.streaming_content), self.data[-5:])

    def test_notes_gated(self):
        url = reverse('courses:download_notes', args=[self.paid_lesson.id])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 notes')

    def test_no_public_url_to_protected_files(self):
        self.assertEqual(self.client.get('/media/videos/v.mp4').status_code, 404)
        self.assertEqual(self.client.get('/protected_media/videos/v.mp4').status_code, 404)


PESAPAL_OK = {'order_tracking_id': 'trk-1', 'redirect_url': 'https://pay.example/redirect'}


@override_settings(PESAPAL_CONSUMER_KEY='k', PESAPAL_CONSUMER_SECRET='s', PESAPAL_IPN_ID='i')
class Payments(Base):
    def test_checkout_requires_login_and_phone(self):
        url = reverse('payments:checkout', args=[self.course.id])
        self.assertEqual(self.client.get(url).status_code, 302)
        nophone = User.objects.create_user('nophone', 'n@x.com', 'pw12345!x')
        self.client.force_login(nophone)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)

    def test_checkout_get_does_not_create_payment(self):
        self.client.force_login(self.student)
        r = self.client.get(reverse('payments:checkout', args=[self.course.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Payment.objects.count(), 0)

    @mock.patch('payments.views.pesapal.submit_order', return_value=PESAPAL_OK)
    def test_checkout_post_redirects_to_pesapal(self, m):
        self.client.force_login(self.student)
        r = self.client.post(reverse('payments:checkout', args=[self.course.id]))
        self.assertRedirects(r, 'https://pay.example/redirect', fetch_redirect_response=False)
        p = Payment.objects.get()
        self.assertEqual(p.amount, Decimal('30000'))
        self.assertEqual(p.pesapal_order_tracking_id, 'trk-1')
        self.assertEqual(p.status, 'pending')

    @mock.patch('payments.views.pesapal.submit_order', side_effect=RuntimeError('boom'))
    def test_pesapal_down_fails_gracefully(self, m):
        self.client.force_login(self.student)
        r = self.client.post(reverse('payments:checkout', args=[self.course.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payment.objects.get().status, 'failed')

    @mock.patch('payments.views.pesapal.submit_order', return_value={'error': {'message': 'bad keys'}})
    def test_pesapal_error_payload_fails_gracefully(self, m):
        self.client.force_login(self.student)
        r = self.client.post(reverse('payments:checkout', args=[self.course.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payment.objects.get().status, 'failed')

    def test_free_course_enrolls_without_pesapal(self):
        free = Course.objects.create(title='Free course', price=0, teacher=self.teacher)
        self.client.force_login(self.student)
        r = self.client.post(reverse('payments:checkout', args=[free.id]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Enrollment.objects.get(user=self.student, course=free).is_active())

    @mock.patch('payments.views.pesapal.get_transaction_status',
                return_value={'payment_status_description': 'Completed', 'payment_method': 'MtnMobileMoney', 'confirmation_code': 'C1'})
    def test_ipn_completed_unlocks_course_with_expiry(self, m):
        self.course.access_days = 30
        self.course.save()
        p = Payment.objects.create(user=self.student, course=self.course, amount=30000,
                                   merchant_reference='ref-1', pesapal_order_tracking_id='trk-1')
        r = self.client.get(reverse('payments:ipn'), {'OrderTrackingId': 'trk-1', 'OrderMerchantReference': 'ref-1', 'OrderNotificationType': 'IPNCHANGE'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 200)
        p.refresh_from_db()
        self.assertEqual((p.status, p.method, p.momo_code), ('success', 'mtn', 'C1'))
        e = Enrollment.objects.get(user=self.student, course=self.course)
        self.assertTrue(e.is_paid)
        self.assertAlmostEqual((e.expiry_date - timezone.now()).days, 29, delta=1)

    @mock.patch('payments.views.pesapal.get_transaction_status', side_effect=RuntimeError('down'))
    def test_ipn_survives_pesapal_errors(self, m):
        Payment.objects.create(user=self.student, course=self.course, amount=1, merchant_reference='ref-2', pesapal_order_tracking_id='t')
        r = self.client.get(reverse('payments:ipn'), {'OrderTrackingId': 't', 'OrderMerchantReference': 'ref-2'})
        self.assertEqual(r.status_code, 200)

    def test_ipn_unknown_reference_is_ok(self):
        r = self.client.get(reverse('payments:ipn'), {'OrderTrackingId': 'x', 'OrderMerchantReference': 'nope'})
        self.assertEqual(r.status_code, 200)

    @mock.patch('payments.views.pesapal.get_transaction_status', return_value={'payment_status_description': 'Failed'})
    def test_failed_payment_does_not_unlock(self, m):
        Payment.objects.create(user=self.student, course=self.course, amount=1, merchant_reference='ref-3', pesapal_order_tracking_id='t3')
        self.client.get(reverse('payments:ipn'), {'OrderTrackingId': 't3', 'OrderMerchantReference': 'ref-3'})
        self.assertFalse(Enrollment.objects.exists())

    @mock.patch('payments.views.pesapal.get_transaction_status',
                return_value={'payment_status_description': 'Completed'})
    def test_callback_only_for_own_payment(self, m):
        Payment.objects.create(user=self.student, course=self.course, amount=1, merchant_reference='ref-4', pesapal_order_tracking_id='t4')
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(reverse('payments:callback'), {'OrderTrackingId': 't4'}).status_code, 404)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('payments:callback'), {'OrderTrackingId': 't4'}).status_code, 200)
        self.assertTrue(Enrollment.objects.get(user=self.student).is_paid)

    def test_admin_approve_requires_post_and_admin(self):
        p = Payment.objects.create(user=self.student, course=self.course, amount=1, merchant_reference='ref-5')
        url = reverse('payments:approve_payment', args=[p.id])
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(Enrollment.objects.get(user=self.student).is_paid)

    def test_admin_payments_page_has_post_form(self):
        Payment.objects.create(user=self.student, course=self.course, amount=1, merchant_reference='ref-6')
        self.client.force_login(self.admin)
        r = self.client.get(reverse('payments:admin_payments'))
        self.assertContains(r, 'method="post"')


class QuizzesCertificatesReviews(Base):
    def setUp(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        self.quiz = Quiz.objects.create(lesson=self.paid_lesson, title='Q', pass_mark_percent=50)
        self.q1 = Question.objects.create(quiz=self.quiz, text='1?', choice_a='a', choice_b='b', correct_choice='a')
        self.q2 = Question.objects.create(quiz=self.quiz, text='2?', choice_a='a', choice_b='b', correct_choice='b')

    def test_fail_then_pass_issues_one_certificate(self):
        self.client.force_login(self.student)
        url = reverse('quizzes:take_quiz', args=[self.quiz.id])
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {f'q{self.q1.id}': 'b', f'q{self.q2.id}': 'a'})
        self.assertContains(r, '0%')
        self.assertFalse(Certificate.objects.exists())
        self.client.post(url, {f'q{self.q1.id}': 'a', f'q{self.q2.id}': 'b'})
        self.client.post(url, {f'q{self.q1.id}': 'a', f'q{self.q2.id}': 'b'})
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(QuizAttempt.objects.count(), 3)
        cert = Certificate.objects.get()
        self.assertEqual(self.client.get(reverse('certificates:verify', args=[cert.certificate_code])).status_code, 200)
        self.assertEqual(self.client.get(reverse('certificates:verify', args=['NOPE'])).status_code, 404)

    def test_unpaid_cannot_take_quiz(self):
        Enrollment.objects.all().delete()
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(reverse('quizzes:take_quiz', args=[self.quiz.id]), {}).status_code, 302)
        self.assertEqual(QuizAttempt.objects.count(), 0)

    def test_review_rules(self):
        url = reverse('reviews:add_review', args=[self.course.id])
        self.client.force_login(self.student)
        self.client.post(url, {'rating': '5', 'comment': 'great'})
        self.client.post(url, {'rating': '4', 'comment': 'edited'})
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.get().rating, 4)
        for bad in ['abc', '9', '0', '']:
            r = self.client.post(url, {'rating': bad})
            self.assertEqual(r.status_code, 302, bad)
        self.assertEqual(Review.objects.get().rating, 4)
        Enrollment.objects.all().delete()
        Review.objects.all().delete()
        self.client.post(url, {'rating': '5'})
        self.assertEqual(Review.objects.count(), 0)
        self.assertEqual(self.client.get(url).status_code, 302)


class RolesAndAccounts(Base):
    def test_role_gates(self):
        admin_only = [reverse('courses:admin_dashboard'), reverse('payments:admin_payments')]
        teach = [reverse('courses:add_course'), reverse('courses:teacher_dashboard')]
        for u in admin_only + teach:
            self.assertEqual(self.client.get(u).status_code, 302, u)
        self.client.force_login(self.student)
        for u in admin_only + teach:
            self.assertEqual(self.client.get(u).status_code, 403, u)
        self.client.force_login(self.teacher)
        for u in teach:
            self.assertEqual(self.client.get(u).status_code, 200, u)
        for u in admin_only:
            self.assertEqual(self.client.get(u).status_code, 403, u)
        self.client.force_login(self.admin)
        for u in admin_only + teach:
            self.assertEqual(self.client.get(u).status_code, 200, u)

    def test_post_login_redirects_by_role(self):
        for user, target in [(self.admin, 'courses:admin_dashboard'), (self.teacher, 'courses:teacher_dashboard'),
                             (self.student, 'courses:my_learning')]:
            self.client.force_login(user)
            self.assertRedirects(self.client.get(reverse('accounts:post_login')), reverse(target))

    def test_blocked_user_cannot_login_and_is_kicked_out(self):
        self.student.is_blocked = True
        self.student.save()
        r = self.client.post(reverse('accounts:login'), {'username': 'stud', 'password': 'pw12345!x'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.student.is_blocked = False
        self.student.save()
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.student.is_blocked = True
        self.student.save()
        r = self.client.get(reverse('courses:my_learning'))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_teacher_manages_only_own_courses(self):
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(reverse('courses:upload_lesson', args=[self.course.id])).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(reverse('courses:upload_lesson', args=[self.course.id])).status_code, 200)

    def test_teacher_created_course_is_owned_by_teacher(self):
        self.client.force_login(self.teacher)
        r = self.client.post(reverse('courses:add_course'), {
            'title': 'New', 'category': 'adr', 'level': 'beginner', 'description': 'd', 'price': '10000', 'is_published': 'on',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Course.objects.get(title='New').teacher, self.teacher)

    def test_profile_page_updates_phone(self):
        self.client.force_login(self.student)
        url = reverse('accounts:profile')
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {'first_name': 'Sam', 'last_name': 'K', 'email': 's@x.com', 'phone': '0779999999'})
        self.assertEqual(r.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual((self.student.first_name, self.student.phone), ('Sam', '0779999999'))
        self.assertEqual(self.client.post(url, {'first_name': 'Sam', 'email': 's@x.com', 'phone': ''}).status_code, 200)

    def test_quiz_builder_permissions_and_flow(self):
        url = reverse('quizzes:manage', args=[self.paid_lesson.id])
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {'action': 'quiz', 'title': 'Lesson quiz', 'pass_mark_percent': '70'})
        quiz = Quiz.objects.get(lesson=self.paid_lesson)
        self.assertEqual(quiz.pass_mark_percent, 70)
        self.client.post(url, {'action': 'question', 'text': 'Q1?', 'choice_a': 'x', 'choice_b': 'y',
                               'choice_c': '', 'choice_d': '', 'correct_choice': 'a'})
        self.assertEqual(quiz.questions.count(), 1)
        q = quiz.questions.get()
        self.client.post(url, {'action': 'delete_question', 'question_id': q.id})
        self.assertEqual(quiz.questions.count(), 0)


class Pwa(Base):
    def test_manifest_and_sw(self):
        m = self.client.get(reverse('core:manifest'))
        self.assertEqual(m['Content-Type'], 'application/manifest+json')
        self.assertEqual(m.json()['display'], 'standalone')
        sw = self.client.get(reverse('core:service_worker'))
        self.assertEqual(sw['Content-Type'], 'application/javascript')
        self.assertEqual(sw['Service-Worker-Allowed'], '/')

    def test_icons_exist(self):
        for name in ['icon-192.png', 'icon-512.png', 'icon-512-maskable.png', 'icon-180.png']:
            self.assertEqual(self.client.get('/static/core/' + name).status_code, 200, name)
        for name in ['phones', 'justice', 'gavel', 'library']:
            self.assertEqual(self.client.get('/static/core/photos/%s.jpg' % name).status_code, 200, name)


class Health(Base):
    @override_settings(DEBUG=True)
    def test_healthz_reports_ok(self):
        r = self.client.get('/healthz/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')
        self.assertNotIn('password', r.content.decode().lower())
