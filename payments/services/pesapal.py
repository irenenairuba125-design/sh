"""Thin wrapper around the Pesapal API v3 (https://developer.pesapal.com), which is what
actually talks to MTN MoMo, Airtel Money, Visa and Mastercard on Pesapal's hosted payment
page. You need a Pesapal merchant account and API keys in .env before this works - see
README.md for the exact steps (sandbox first, then live).
"""

import requests
from django.conf import settings

BASE_URLS = {
    'sandbox': 'https://cybqa.pesapal.com/pesapalv3',
    'live': 'https://pay.pesapal.com/v3',
}


def _base_url():
    return BASE_URLS['live'] if settings.PESAPAL_ENV == 'live' else BASE_URLS['sandbox']


def get_access_token():
    url = f'{_base_url()}/api/Auth/RequestToken'
    payload = {
        'consumer_key': settings.PESAPAL_CONSUMER_KEY,
        'consumer_secret': settings.PESAPAL_CONSUMER_SECRET,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()['token']


def register_ipn(ipn_url):
    """One-time setup: tells Pesapal where to send payment notifications. Run this via
    `python manage.py register_ipn --url https://yourdomain.com/payments/ipn/` and copy
    the returned ipn_id into PESAPAL_IPN_ID in .env."""
    token = get_access_token()
    url = f'{_base_url()}/api/URLSetup/RegisterIPN'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {'url': ipn_url, 'ipn_notification_type': 'GET'}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def submit_order(payment, callback_url):
    token = get_access_token()
    url = f'{_base_url()}/api/Transactions/SubmitOrderRequest'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        'id': payment.merchant_reference,
        'currency': 'UGX',
        'amount': float(payment.amount),
        'description': f'Payment for {payment.course.title}'[:100],
        'callback_url': callback_url,
        'notification_id': settings.PESAPAL_IPN_ID,
        'billing_address': {
            'email_address': payment.user.email or 'student@example.com',
            'phone_number': payment.user.phone,
            'first_name': payment.user.first_name or payment.user.username,
            'last_name': payment.user.last_name or '',
        },
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()  # {order_tracking_id, redirect_url, merchant_reference}


def get_transaction_status(order_tracking_id):
    token = get_access_token()
    url = f'{_base_url()}/api/Transactions/GetTransactionStatus'
    headers = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, params={'orderTrackingId': order_tracking_id}, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()
