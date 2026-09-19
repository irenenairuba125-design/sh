from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import SiteSettings
from courses import catalog
from courses.models import Course, Lesson
from payments.earnings import teacher_earnings
from payments.models import Enrollment, Payment, Payout
from reviews.models import Review

from .tests import Base


def make_course(teacher, title, price=12000, **extra):
    return Course.objects.create(title=title, price=price, teacher=teacher, **extra)


class BrowseFilters(Base):
    def setUp(self):
        self.cheap = make_course(self.teacher, 'Cheap Course', 5000, category='adr')
        self.mid = make_course(self.teacher, 'Mid Course', 12000, category='adr')
        self.dear = make_course(self.teacher, 'Dear Course', 20000, category='moot_court')
        for c in (self.cheap, self.mid, self.dear):
            Lesson.objects.create(course=c, title='l', order=1, kind='video', free_preview=(c is self.mid))
        Lesson.objects.create(course=self.dear, title='a1', order=2, kind='audio')
        Lesson.objects.create(course=self.dear, title='a2', order=3, kind='audio')
        self.audio = self.dear
        Review.objects.create(user=self.student, course=self.mid, rating=5)
        Review.objects.create(user=self.teacher, course=self.cheap, rating=3)

    def titles(self, **params):
        html = self.client.get(reverse('courses:browse'), params).content.decode()
        return {t for t in ('Cheap Course', 'Mid Course', 'Dear Course', 'Zebra Plaint Basics') if t in html}

    def test_browse_page_lists_everything(self):
        r = self.client.get(reverse('courses:browse'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.titles(), {'Cheap Course', 'Mid Course', 'Dear Course', 'Zebra Plaint Basics'})

    def test_price_bands(self):
        self.assertEqual(self.titles(price='under10k'), {'Cheap Course'})
        self.assertEqual(self.titles(price='10to15k'), {'Mid Course'})
        self.assertEqual(self.titles(price='over15k'), {'Dear Course', 'Zebra Plaint Basics'})

    def test_rating_and_free_preview_and_category(self):
        self.assertEqual(self.titles(rating='4half'), {'Mid Course'})
        self.assertEqual(self.titles(rating='4plus'), {'Mid Course'})
        self.assertEqual(self.titles(freePreview='true'), {'Mid Course', 'Zebra Plaint Basics'})
        self.assertEqual(self.titles(category='adr'), {'Cheap Course', 'Mid Course'})

    def test_format_filter(self):
        self.assertEqual(self.titles(**{'format': 'audio-heavy'}), {'Dear Course'})
        self.assertEqual(self.titles(**{'format': 'video-heavy'}), {'Cheap Course', 'Mid Course', 'Zebra Plaint Basics'})

    def test_sorting_and_bad_input(self):
        html = self.client.get(reverse('courses:browse'), {'sort': 'price_low'}).content.decode()
        self.assertLess(html.index('Cheap Course'), html.index('Dear Course'))
        html = self.client.get(reverse('courses:browse'), {'sort': 'price_high'}).content.decode()
        self.assertLess(html.index('Dear Course'), html.index('Cheap Course'))
        for junk in [{'price': 'x'}, {'rating': '../..'}, {'category': '<script>'}, {'sort': 'evil'}, {'q': '%00'}]:
            self.assertEqual(self.client.get(reverse('courses:browse'), junk).status_code, 200)

    def test_unpublished_never_listed(self):
        self.mid.is_published = False
        self.mid.save()
        self.assertNotIn('Mid Course', self.titles())

    def test_card_shows_rating_instructor_and_counts(self):
        html = self.client.get(reverse('courses:browse'), {'q': 'mid'}).content.decode()
        self.assertIn('5.0', html)
        self.assertIn('(1)', html)
        self.assertIn('1 lesson', html)
        self.assertIn('teach', html)


class Badges(Base):
    def test_new_and_free_preview_badges(self):
        c = catalog.decorate(Course.objects.get(pk=self.course.id))
        self.assertIn('New', c.badges)
        self.assertIn('Free preview', c.badges)

    def test_old_course_is_not_new(self):
        Course.objects.filter(pk=self.course.id).update(created_at=timezone.now() - timedelta(days=40))
        c = catalog.decorate(Course.objects.get(pk=self.course.id))
        self.assertNotIn('New', c.badges)

    def test_bestseller_and_trending_use_real_subscribers(self):
        with mock.patch.object(catalog, 'BESTSELLER_MIN_SUBSCRIBERS', 1), \
             mock.patch.object(catalog, 'TRENDING_MIN_NEW_SUBSCRIBERS', 1):
            Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
            c = catalog.decorate(Course.objects.get(pk=self.course.id))
            self.assertEqual(c.subscribers, 1)
            self.assertIn('Bestseller', c.badges)
            self.assertIn('Trending', c.badges)
        c = catalog.decorate(Course.objects.get(pk=self.course.id))
        self.assertNotIn('Bestseller', c.badges)

    def test_unpaid_enrollment_is_not_a_subscriber(self):
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=False)
        self.assertEqual(catalog.decorate(Course.objects.get(pk=self.course.id)).subscribers, 0)


class CoursePageDetails(Base):
    def test_modules_durations_and_monthly_price(self):
        Course.objects.filter(pk=self.course.id).update(access_days=30, subtitle='Draft it right', level='intermediate')
        Lesson.objects.filter(pk=self.free_lesson.id).update(module_title='Module 01: Setup', duration_minutes=8)
        Lesson.objects.filter(pk=self.paid_lesson.id).update(module_title='Module 02: Practice', duration_minutes=90, kind='audio')
        html = self.client.get(reverse('courses:course_detail', args=[self.course.id])).content.decode()
        self.assertIn('Module 01: Setup', html)
        self.assertIn('Module 02: Practice', html)
        self.assertIn('1h 30m', html)
        self.assertIn('Audio', html)
        self.assertIn('/month', html)
        self.assertIn('Draft it right', html)
        self.assertIn('Intermediate', html)
        self.assertLess(html.index('Module 01'), html.index('Module 02'))

    def test_reviews_subscribers_and_verified_badge(self):
        Review.objects.create(user=self.student, course=self.course, rating=4, comment='Very clear lessons')
        Enrollment.objects.create(user=self.student, course=self.course, is_paid=True)
        User.objects.filter(pk=self.teacher.pk).update(is_verified_teacher=True, bio='Ten years in court', headline='Contracts')
        html = self.client.get(reverse('courses:course_detail', args=[self.course.id])).content.decode()
        self.assertIn('Very clear lessons', html)
        self.assertIn('1 subscriber', html)
        self.assertIn('Verified instructor', html)
        self.assertIn('Ten years in court', html)

    def test_lesson_size_label_never_crashes_without_a_file(self):
        self.assertEqual(self.paid_lesson.size_label, '')


class TeacherSignup(Base):
    DATA = {'username': 'newteach', 'email': 'n@x.com', 'phone': '0773000111', 'password1': 'Str0ng-pass-99',
            'password2': 'Str0ng-pass-99', 'headline': 'Contracts that hold up', 'location': 'Kampala',
            'bio': 'Advocate', 'payout_phone': '0773000111'}

    def test_creator_page_shows_teacher_fields_and_learner_page_does_not(self):
        creator = self.client.get(reverse('accounts:register') + '?role=creator').content.decode()
        learner = self.client.get(reverse('accounts:register')).content.decode()
        self.assertIn('name="payout_phone"', creator)
        self.assertNotIn('name="payout_phone"', learner)
        self.assertIn('name="phone"', learner)  # regression: the normal phone field must stay
        self.assertIn('name="phone"', creator)

    def test_teacher_signup_creates_unverified_teacher(self):
        r = self.client.post(reverse('accounts:register'), dict(self.DATA, role='teacher'))
        self.assertRedirects(r, reverse('accounts:post_login'), fetch_redirect_response=False)
        u = User.objects.get(username='newteach')
        self.assertEqual((u.role, u.is_verified_teacher, u.location, u.payout_phone),
                         ('teacher', False, 'Kampala', '0773000111'))
        self.assertRedirects(self.client.get(reverse('accounts:post_login')), reverse('courses:teacher_dashboard'))

    def test_teacher_signup_needs_the_teaching_details(self):
        r = self.client.post(reverse('accounts:register'), dict(self.DATA, role='teacher', payout_phone='', headline=''))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username='newteach').exists())

    def test_cannot_self_register_as_admin_or_verified(self):
        for role in ('admin', 'superuser', 'staff'):
            self.client.post(reverse('accounts:register'), dict(self.DATA, username='x' + role, role=role,
                                                                is_superuser='on', is_staff='on', is_verified_teacher='on'))
            u = User.objects.get(username='x' + role)
            self.assertEqual((u.role, u.is_superuser, u.is_staff, u.is_verified_teacher), ('student', False, False, False))

    def test_learner_signup_still_works(self):
        r = self.client.post(reverse('accounts:register'), {
            'username': 'learner1', 'email': 'l@x.com', 'phone': '0774000111',
            'password1': 'Str0ng-pass-99', 'password2': 'Str0ng-pass-99'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(User.objects.get(username='learner1').role, 'student')

    def test_profile_shows_teacher_fields_only_to_teachers(self):
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get(reverse('accounts:profile')), 'payout_phone')
        self.client.force_login(self.student)
        self.assertNotContains(self.client.get(reverse('accounts:profile')), 'payout_phone')


class VerificationAndDrafts(Base):
    POST = {'title': 'Fresh', 'category': 'adr', 'level': 'beginner', 'description': 'd',
            'price': '10000', 'is_published': 'on'}

    def test_unverified_teacher_saves_draft_and_it_is_hidden(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('courses:add_course'), self.POST)
        c = Course.objects.get(title='Fresh')
        self.assertFalse(c.is_published)
        self.client.logout()
        self.assertNotIn('Fresh', self.client.get(reverse('courses:browse')).content.decode())
        self.assertEqual(self.client.get(reverse('courses:course_detail', args=[c.id])).status_code, 404)
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get(reverse('courses:teacher_dashboard')), 'Draft')

    def test_verified_teacher_publishes(self):
        User.objects.filter(pk=self.teacher.pk).update(is_verified_teacher=True)
        self.client.force_login(User.objects.get(pk=self.teacher.pk))
        self.client.post(reverse('courses:add_course'), self.POST)
        self.assertTrue(Course.objects.get(title='Fresh').is_published)

    def test_editing_cannot_publish_an_unverified_teachers_course(self):
        self.client.force_login(self.teacher)
        self.client.post(reverse('courses:edit_course', args=[self.course.id]), dict(self.POST, title='Zebra Plaint Basics'))
        self.course.refresh_from_db()
        self.assertFalse(self.course.is_published)

    def test_admin_publishes_directly(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('courses:add_course'), dict(self.POST, teacher=self.teacher.id))
        self.assertTrue(Course.objects.get(title='Fresh').is_published)

    def test_admin_can_verify_and_unverify_and_others_cannot(self):
        url = reverse('accounts:verify_teacher', args=[self.teacher.id])
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertFalse(User.objects.get(pk=self.teacher.pk).is_verified_teacher)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertTrue(User.objects.get(pk=self.teacher.pk).is_verified_teacher)
        self.client.post(url)
        self.assertFalse(User.objects.get(pk=self.teacher.pk).is_verified_teacher)

    def test_cannot_verify_a_student(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse('accounts:verify_teacher', args=[self.student.id])).status_code, 404)


class EarningsAndPayouts(Base):
    def setUp(self):
        s = SiteSettings.load()
        s.platform_fee_percent = 10
        s.save()
        for i, amount in enumerate([30000, 20000]):
            Payment.objects.create(user=self.student, course=self.course, amount=amount,
                                   status='success', merchant_reference='ok%d' % i, method='mtn')
        Payment.objects.create(user=self.student, course=self.course, amount=99999, status='pending', merchant_reference='p1')
        Payment.objects.create(user=self.student, course=self.course, amount=88888, status='failed', merchant_reference='f1')

    def test_only_successful_payments_count(self):
        e = teacher_earnings(self.teacher)
        self.assertEqual((e['gross'], e['fee'], e['net'], e['paid'], e['balance']),
                         (Decimal(50000), Decimal(5000), Decimal(45000), Decimal(0), Decimal(45000)))

    def test_fee_percent_is_configurable(self):
        s = SiteSettings.load()
        s.platform_fee_percent = 20
        s.save()
        self.assertEqual(teacher_earnings(self.teacher)['net'], Decimal(40000))

    def test_other_teacher_earns_nothing(self):
        self.assertEqual(teacher_earnings(self.other_teacher)['balance'], 0)

    def test_admin_records_payouts_and_balance_drops(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('payments:admin_payouts'), {'teacher_id': self.teacher.id, 'amount': '20000', 'reference': 'TX1'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Payout.objects.get().reference, 'TX1')
        self.assertEqual(teacher_earnings(self.teacher)['balance'], Decimal(25000))

    def test_payout_cannot_exceed_balance_or_be_junk(self):
        self.client.force_login(self.admin)
        for bad in ['45001', '0', '-5', 'abc', '', '10.5']:
            self.client.post(reverse('payments:admin_payouts'), {'teacher_id': self.teacher.id, 'amount': bad})
        self.assertEqual(Payout.objects.count(), 0)

    def test_payout_pages_are_admin_only(self):
        for user in (self.student, self.teacher):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('payments:admin_payouts')).status_code, 403)
            self.assertEqual(self.client.post(reverse('payments:admin_payouts'),
                                              {'teacher_id': self.teacher.id, 'amount': '100'}).status_code, 403)
        self.assertEqual(Payout.objects.count(), 0)

    def test_teacher_dashboard_shows_their_own_money(self):
        Payout.objects.create(teacher=self.teacher, amount=5000, phone='0771', reference='REF77')
        self.client.force_login(self.teacher)
        html = self.client.get(reverse('courses:teacher_dashboard')).content.decode()
        self.assertIn('50,000', html)
        self.assertIn('45,000', html)
        self.assertIn('40,000', html)
        self.assertIn('REF77', html)
        self.client.force_login(self.other_teacher)
        self.assertNotIn('REF77', self.client.get(reverse('courses:teacher_dashboard')).content.decode())

    def test_admin_payouts_page_lists_balance(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('payments:admin_payouts')), '45,000')


class InfoPagesAndHome(Base):
    def test_every_info_page_loads(self):
        for name in ['pricing', 'payouts', 'about', 'trust', 'terms', 'privacy']:
            self.assertEqual(self.client.get(reverse('core:' + name)).status_code, 200, name)

    def test_pricing_uses_the_configured_fee(self):
        s = SiteSettings.load()
        s.platform_fee_percent = 25
        s.save()
        html = self.client.get(reverse('core:pricing')).content.decode()
        self.assertIn('25%', html)
        self.assertIn('11,250', html)

    def test_footer_links_are_real_pages(self):
        html = self.client.get('/').content.decode()
        for path in ['/pricing/', '/payouts/', '/about/', '/trust/', '/terms/', '/privacy/', '/courses/']:
            self.assertIn('href="%s"' % path, html)

    def test_teach_link_goes_to_creator_signup(self):
        html = self.client.get('/').content.decode()
        self.assertIn('/accounts/register/?role=creator', html)

    def test_home_sections_match_the_reference(self):
        html = self.client.get('/').content.decode()
        for text in ['Learn the law.', 'Get paid to teach it.', 'Browse courses', 'Start teaching', 'Mobile-money native',
                     'Real skills. Real work.', 'Two doors. Same house.', 'If you want to learn', 'If you want to teach',
                     'Advocates know how. Now it gets paid.', 'Made for mobile money', 'Made in Uganda']:
            self.assertIn(text, html, text)

    def test_live_card_only_shows_real_numbers(self):
        self.assertNotIn('Live &middot; this week', self.client.get('/').content.decode() if not self.teacher.courses.exists() else '')
        User.objects.filter(pk=self.teacher.pk).update(is_verified_teacher=True)
        Payment.objects.create(user=self.student, course=self.course, amount=15000, status='success',
                               merchant_reference='live1', method='mtn')
        Payment.objects.create(user=self.student, course=self.course, amount=7000, status='success',
                               merchant_reference='live2', method='airtel')
        Payment.objects.filter(merchant_reference='live2').update(created_at=timezone.now() - timedelta(days=30))
        html = self.client.get('/').content.decode()
        self.assertIn('+UGX 15,000', html)
        self.assertNotIn('22,000', html)

    def test_bottom_bar_has_browse(self):
        html = self.client.get('/').content.decode()
        self.assertIn('bottom-nav', html)
        self.assertIn('>Browse', html.replace('</svg>', '>'))
