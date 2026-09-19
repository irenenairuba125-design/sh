import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import role_required
from core.models import SiteSettings
from courses.models import Course
from .earnings import teacher_earnings
from .models import Enrollment, Payment, Payout
from .services import pesapal


def pesapal_configured():
    return bool(settings.PESAPAL_CONSUMER_KEY and settings.PESAPAL_CONSUMER_SECRET and settings.PESAPAL_IPN_ID)


@login_required
def checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id, is_published=True)

    existing = Enrollment.objects.filter(user=request.user, course=course).first()
    if existing and existing.is_active():
        messages.info(request, 'You already have access to this course.')
        return redirect('courses:course_detail', pk=course.id)

    if course.price > 0 and not request.user.phone:
        messages.error(request, 'Add your phone number to your account before paying with mobile money.')
        return redirect('accounts:profile')

    if request.method != 'POST':
        return render(request, 'payments/checkout.html', {
            'course': course,
            'pesapal_enabled': pesapal_configured(),
            'momo_number': SiteSettings.load().momo_number,
            'pending': Payment.objects.filter(user=request.user, course=course, status=Payment.Status.PENDING).exclude(momo_code='').first(),
        })

    if course.price <= 0:
        _grant_access(Payment(user=request.user, course=course))
        messages.success(request, 'You are enrolled in this free course.')
        return redirect('courses:course_detail', pk=course.id)

    if not pesapal_configured():
        messages.error(request, 'Online payment is not switched on yet. Please use the manual mobile-money option.')
        return redirect('payments:checkout', course_id=course.id)

    payment = Payment.objects.create(
        user=request.user,
        course=course,
        amount=course.price,
        merchant_reference=str(uuid.uuid4()),
    )
    callback_url = request.build_absolute_uri(reverse('payments:callback'))
    try:
        result = pesapal.submit_order(payment, callback_url)
    except Exception:
        result = {}

    if not result.get('redirect_url'):
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=['status'])
        messages.error(request, 'Could not reach the payment provider. Please try again shortly.')
        return redirect('courses:course_detail', pk=course.id)

    payment.pesapal_order_tracking_id = result.get('order_tracking_id', '')
    payment.save(update_fields=['pesapal_order_tracking_id'])
    return redirect(result['redirect_url'])


def _finalize_payment(payment):
    """The single place that turns a Pesapal status check into is_paid=True. Called from
    both the browser callback (payment_callback) and the server-to-server IPN
    (payment_ipn) - the IPN is the one that's actually reliable if the student closes
    their browser mid-payment."""
    if payment.status == Payment.Status.SUCCESS:
        return payment

    status_data = pesapal.get_transaction_status(payment.pesapal_order_tracking_id)
    status_desc = (status_data.get('payment_status_description') or '').upper()
    payment.momo_code = status_data.get('confirmation_code', '') or payment.momo_code

    method = (status_data.get('payment_method') or '').lower()
    if 'mtn' in method:
        payment.method = Payment.Method.MTN
    elif 'airtel' in method:
        payment.method = Payment.Method.AIRTEL
    elif 'visa' in method or 'master' in method or 'card' in method:
        payment.method = Payment.Method.CARD

    if status_desc == 'COMPLETED':
        payment.status = Payment.Status.SUCCESS
        payment.save()
        _grant_access(payment)
    elif status_desc in ('FAILED', 'INVALID'):
        payment.status = Payment.Status.FAILED
        payment.save()
    else:
        payment.save()
    return payment


def _grant_access(payment):
    enrollment, _ = Enrollment.objects.get_or_create(user=payment.user, course=payment.course)
    enrollment.is_paid = True
    if payment.course.access_days:
        enrollment.expiry_date = timezone.now() + timedelta(days=payment.course.access_days)
    else:
        enrollment.expiry_date = None
    enrollment.save()


@login_required
@require_POST
def manual_payment(request, course_id):
    """Student sent money to the school's MTN/Airtel number and reports the transaction ID.
    The course stays locked until an admin approves it on the Payments page."""
    course = get_object_or_404(Course, pk=course_id, is_published=True)
    back = redirect('payments:checkout', course_id=course.id)

    existing = Enrollment.objects.filter(user=request.user, course=course).first()
    if existing and existing.is_active():
        return redirect('courses:course_detail', pk=course.id)
    if not SiteSettings.load().momo_number:
        messages.error(request, 'Manual payment is not set up yet. Please contact the school.')
        return back

    method = request.POST.get('method')
    if method not in (Payment.Method.MTN, Payment.Method.AIRTEL):
        method = Payment.Method.OTHER
    transaction_id = re.sub(r'\s+', '', request.POST.get('transaction_id', '')).upper()
    payer_phone = re.sub(r'[^0-9+]', '', request.POST.get('payer_phone', ''))[:20]

    if not re.fullmatch(r'[A-Z0-9]{6,40}', transaction_id):
        messages.error(request, 'Enter the transaction ID from your mobile-money confirmation message (letters and numbers only).')
        return back
    if len(payer_phone) < 9:
        messages.error(request, 'Enter the phone number you paid from.')
        return back
    if Payment.objects.filter(momo_code=transaction_id).exclude(status=Payment.Status.FAILED).exists():
        messages.error(request, 'That transaction ID has already been used.')
        return back

    Payment.objects.create(
        user=request.user, course=course, amount=course.price, method=method,
        merchant_reference=str(uuid.uuid4()), momo_code=transaction_id, payer_phone=payer_phone,
    )
    messages.success(request, 'Thank you. We are confirming your payment and will unlock the course as soon as it is verified.')
    return redirect('courses:course_detail', pk=course.id)


@login_required
def payment_callback(request):
    """The student's browser lands here after Pesapal's hosted payment page."""
    order_tracking_id = request.GET.get('OrderTrackingId')
    payment = get_object_or_404(Payment, pesapal_order_tracking_id=order_tracking_id, user=request.user)
    try:
        payment = _finalize_payment(payment)
    except Exception:
        messages.warning(request, 'We could not confirm your payment yet. It will unlock automatically once confirmed.')
    return render(request, 'payments/payment_status.html', {'payment': payment})


def payment_ipn(request):
    """Pesapal calls this server-to-server. Must respond 200 with this exact JSON shape
    or Pesapal will keep retrying. No @login_required here - Pesapal isn't logged in."""
    order_tracking_id = request.GET.get('OrderTrackingId')
    merchant_reference = request.GET.get('OrderMerchantReference')

    payment = Payment.objects.filter(merchant_reference=merchant_reference or '').first()
    if payment:
        if order_tracking_id and not payment.pesapal_order_tracking_id:
            payment.pesapal_order_tracking_id = order_tracking_id
            payment.save(update_fields=['pesapal_order_tracking_id'])
        try:
            _finalize_payment(payment)
        except Exception:
            pass  # still ack with 200; Pesapal will call again and the admin can approve manually

    return JsonResponse({
        'orderNotificationType': request.GET.get('OrderNotificationType', 'IPNCHANGE'),
        'orderTrackingId': order_tracking_id,
        'orderMerchantReference': merchant_reference,
        'status': 200,
    })


@role_required('admin')
def admin_payments(request):
    payments = sorted(
        Payment.objects.select_related('user', 'course'),
        key=lambda p: (p.status != Payment.Status.PENDING or not p.momo_code, -p.created_at.timestamp()),
    )
    return render(request, 'payments/admin_payments.html', {'payments': payments})


@role_required('admin')
@require_POST
def approve_payment(request, payment_id):
    """Manual fallback for when a student pays informally (e.g. sends money directly
    and messages you) rather than through the Pesapal flow above."""
    payment = get_object_or_404(Payment, pk=payment_id)
    payment.status = Payment.Status.SUCCESS
    payment.save()
    _grant_access(payment)
    messages.success(request, f'Payment approved. {payment.user} now has access to {payment.course}.')
    return redirect('payments:admin_payments')


@role_required('admin')
@require_POST
def reject_payment(request, payment_id):
    payment = get_object_or_404(Payment, pk=payment_id)
    if payment.status != Payment.Status.SUCCESS:
        payment.status = Payment.Status.FAILED
        payment.save()
        messages.success(request, 'Payment rejected.')
    else:
        messages.error(request, 'That payment was already approved.')
    return redirect('payments:admin_payments')


@role_required('admin')
def admin_payouts(request):
    from decimal import Decimal, InvalidOperation

    from accounts.models import User

    if request.method == 'POST':
        teacher = get_object_or_404(User, pk=request.POST.get('teacher_id'), role=User.Role.TEACHER)
        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except InvalidOperation:
            amount = Decimal(0)
        balance = teacher_earnings(teacher)['balance']
        if amount <= 0 or amount != amount.to_integral_value():
            messages.error(request, 'Enter a whole amount above zero.')
        elif amount > balance:
            messages.error(request, 'That is more than the balance owed to this teacher.')
        else:
            Payout.objects.create(
                teacher=teacher, amount=amount, phone=teacher.payout_phone,
                reference=request.POST.get('reference', '').strip()[:100],
            )
            messages.success(request, 'Recorded a payout of UGX %s to %s.' % (f'{int(amount):,}', teacher.username))
        return redirect('payments:admin_payouts')

    rows = []
    for teacher in User.objects.filter(role=User.Role.TEACHER).order_by('username'):
        data = teacher_earnings(teacher)
        data['teacher'] = teacher
        rows.append(data)
    rows.sort(key=lambda r: -r['balance'])
    return render(request, 'payments/admin_payouts.html', {
        'rows': rows,
        'recent': Payout.objects.select_related('teacher')[:15],
    })
