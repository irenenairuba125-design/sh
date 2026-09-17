from django.conf import settings
from django.core.management.base import BaseCommand

from payments.services import pesapal


class Command(BaseCommand):
    help = (
        'Registers your /payments/ipn/ endpoint with Pesapal and prints the IPN ID to '
        'put in .env as PESAPAL_IPN_ID. The URL must be publicly reachable - use an '
        'ngrok tunnel for local testing, your real domain in production.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--url', help='Full public URL to your /payments/ipn/ endpoint')

    def handle(self, *args, **options):
        url = options['url'] or f"{settings.SITE_URL.rstrip('/')}/payments/ipn/"
        result = pesapal.register_ipn(url)
        self.stdout.write(self.style.SUCCESS(f'Registered IPN: {result}'))
        self.stdout.write(self.style.WARNING(f"Copy this into your .env -> PESAPAL_IPN_ID={result.get('ipn_id')}"))
