from django.test import override_settings
from django.urls import reverse

from core.models import SiteSettings
from payments.models import Enrollment, Payment

from .tests import Base

NO_PESAPAL = dict(PESAPAL_CONSUMER_KEY='', PESAPAL_CONSUMER_SECRET='', PESAPAL_IPN_ID='')


@override_settings(**NO_PESAPAL)
class ManualPayments(Base):
    def setUp(self):
        s = SiteSettings.load()
        s.momo_number = '0771234567'
        s.save()
        self.url = reverse('payments:manual', args=[self.course.id])
        self.good = {'method': 'mtn', 'payer_phone': '0772000111', 'transaction_id': 'ab12 cd34ef'}

    def test_checkout_shows_school_number_and_hides_online_button(self):
        self.client.force_login(self.student)
        r = self.client.get(reverse('payments:checkout', args=[self.course.id]))
        self.assertContains(r, '0771234567')
        self.assertContains(r, 'Transaction ID')
        self.assertNotContains(r, 'Pay online')

    def test_online_post_without_pesapal_keys_is_refused_politely(self):
        self.client.force_login(self.student)
        r = self.client.post(reverse('payments:checkout', args=[self.course.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)

    def test_full_manual_flow_admin_approves_and_course_unlocks(self):
        self.client.force_login(self.student)
        r = self.client.post(self.url, self.good)
        self.assertEqual(r.status_code, 302)
        p = Payment.objects.get()
        self.assertEqual((p.status, p.method, p.momo_code, p.payer_phone), ('pending', 'mtn', 'AB12CD34EF', '0772000111'))
        self.assertEqual(int(p.amount), 30000)
        paid = reverse('courses:watch_lesson', args=[self.paid_lesson.id])
        self.assertEqual(self.client.get(paid).status_code, 302)  # still locked
        self.assertContains(self.client.get(reverse('courses:my_learning')), 'Waiting for payment confirmation')

        self.client.force_login(self.admin)
        page = self.client.get(reverse('payments:admin_payments'))
        self.assertContains(page, 'AB12CD34EF')
        self.assertEqual(self.client.post(reverse('payments:approve_payment', args=[p.id])).status_code, 302)

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(paid).status_code, 200)  # unlocked
        self.assertTrue(Enrollment.objects.get(user=self.student, course=self.course).is_active())

    def test_reject_keeps_course_locked_and_allows_reuse_of_id(self):
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        p = Payment.objects.get()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('payments:reject_payment', args=[p.id])).status_code, 405)
        self.assertEqual(self.client.post(reverse('payments:reject_payment', args=[p.id])).status_code, 302)
        p.refresh_from_db()
        self.assertEqual(p.status, 'failed')
        self.assertFalse(Enrollment.objects.exists())
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        self.assertEqual(Payment.objects.filter(status='pending').count(), 1)

    def test_students_cannot_approve_or_reject(self):
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        p = Payment.objects.get()
        self.assertEqual(self.client.post(reverse('payments:approve_payment', args=[p.id])).status_code, 403)
        self.assertEqual(self.client.post(reverse('payments:reject_payment', args=[p.id])).status_code, 403)
        self.assertFalse(Enrollment.objects.exists())

    def test_bad_input_is_rejected(self):
        self.client.force_login(self.student)
        for bad in [{'transaction_id': ''}, {'transaction_id': '12'}, {'transaction_id': 'abc def!!'},
                    {'transaction_id': 'ABC123XYZ', 'payer_phone': '12'}]:
            data = dict(self.good, **bad)
            self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)

    def test_transaction_id_cannot_be_reused_by_someone_else(self):
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        self.client.force_login(self.teacher)
        self.client.post(self.url, self.good)
        self.assertEqual(Payment.objects.count(), 1)

    def test_login_and_post_required(self):
        self.assertEqual(self.client.post(self.url, self.good).status_code, 302)
        self.assertEqual(Payment.objects.count(), 0)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_already_enrolled_student_creates_nothing(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        self.assertEqual(Payment.objects.count(), 0)

    def test_manual_disabled_when_no_momo_number(self):
        s = SiteSettings.load()
        s.momo_number = ''
        s.save()
        self.client.force_login(self.student)
        self.client.post(self.url, self.good)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertContains(self.client.get(reverse('payments:checkout', args=[self.course.id])), 'not switched on yet')

    def test_unknown_method_becomes_other(self):
        self.client.force_login(self.student)
        self.client.post(self.url, dict(self.good, method='hacker'))
        self.assertEqual(Payment.objects.get().method, 'other')
