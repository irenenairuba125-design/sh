import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.decorators import role_required
from courses.models import Course
from .models import Enrollment, Payment
from .services import pesapal


@login_required
def checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id, is_published=True)

    existing = Enrollment.objects.filter(user=request.user, course=course).first()
    if existing and existing.is_active():
        messages.info(request, 'You already have access to this course.')
        return redirect('courses:course_detail', pk=course.id)

    if not request.user.phone:
        messages.error(request, 'Add a phone number to your account (in /django-admin/ for now) before paying with mobile money.')
        return redirect('courses:course_detail', pk=course.id)

    if request.method != 'POST':
        return render(request, 'payments/checkout.html', {'course': course})

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
def payment_callback(request):
    """The student's browser lands here after Pesapal's hosted payment page."""
    order_tracking_id = request.GET.get('OrderTrackingId')
    payment = get_object_or_404(Payment, pesapal_order_tracking_id=order_tracking_id, user=request.user)
    payment = _finalize_payment(payment)
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
        _finalize_payment(payment)

    return JsonResponse({
        'orderNotificationType': request.GET.get('OrderNotificationType', 'IPNCHANGE'),
        'orderTrackingId': order_tracking_id,
        'orderMerchantReference': merchant_reference,
        'status': 200,
    })


@role_required('admin')
def admin_payments(request):
    payments = Payment.objects.select_related('user', 'course').order_by('-created_at')
    return render(request, 'payments/admin_payments.html', {'payments': payments})


@role_required('admin')
def approve_payment(request, payment_id):
    """Manual fallback for when a student pays informally (e.g. sends money directly
    and messages you) rather than through the Pesapal flow above."""
    payment = get_object_or_404(Payment, pk=payment_id)
    payment.status = Payment.Status.SUCCESS
    payment.save()
    _grant_access(payment)
    messages.success(request, f'Payment approved. {payment.user} now has access to {payment.course}.')
    return redirect('payments:admin_payments')
