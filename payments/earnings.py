from decimal import Decimal

from django.db.models import Sum

from core.models import SiteSettings
from .models import Payment, Payout


def teacher_earnings(teacher):
    """Gross sales of the teacher's courses, the platform fee, what they earned, what has
    already been paid out, and the balance still owed."""
    gross = Payment.objects.filter(
        course__teacher=teacher, status=Payment.Status.SUCCESS,
    ).aggregate(total=Sum('amount'))['total'] or Decimal(0)
    fee_percent = SiteSettings.load().platform_fee_percent
    fee = (gross * fee_percent / 100).quantize(Decimal(1))
    net = gross - fee
    paid = Payout.objects.filter(teacher=teacher).aggregate(total=Sum('amount'))['total'] or Decimal(0)
    return {
        'gross': gross, 'fee_percent': fee_percent, 'fee': fee,
        'net': net, 'paid': paid, 'balance': net - paid,
    }
