"""Check the SMTP settings without having to register an account first.

    python Backend/manage.py sendtestmail you@gmail.com

Prints the effective configuration, then tries to deliver one real message
and reports the SMTP error verbatim if it fails - that error is the whole
point of the command, since the register/forgot-password pages deliberately
show a generic message instead of leaking why an email did not arrive.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError

HINTS = {
    'authentication': 'Wrong EMAIL_HOST_USER or EMAIL_HOST_PASSWORD. Gmail needs a\n'
                      '  16-character App password (Google Account > Security > 2-Step\n'
                      '  Verification > App passwords), not the normal account password.',
    'timed out': 'Nothing answered on %s:%s - the port is usually blocked by a\n'
                 '  firewall, antivirus or the campus/company network.',
    'ssl': 'TLS/SSL mismatch: use EMAIL_PORT=587 with EMAIL_USE_TLS=1, or\n'
           '  EMAIL_PORT=465 with EMAIL_USE_SSL=1.',
}


class Command(BaseCommand):
    help = 'Send one test email to verify the SMTP configuration in .env'

    def add_arguments(self, parser):
        parser.add_argument('to', help='recipient address')

    def handle(self, *args, **options):
        to_email = options['to']

        self.stdout.write('EMAIL_BACKEND      = %s' % settings.EMAIL_BACKEND)
        self.stdout.write('EMAIL_HOST         = %s:%s' % (settings.EMAIL_HOST, settings.EMAIL_PORT))
        self.stdout.write('EMAIL_USE_TLS/SSL  = %s / %s' % (settings.EMAIL_USE_TLS, settings.EMAIL_USE_SSL))
        self.stdout.write('EMAIL_HOST_USER    = %r' % settings.EMAIL_HOST_USER)
        self.stdout.write('EMAIL_HOST_PASSWORD= %s' % (
            '(set, %d chars)' % len(settings.EMAIL_HOST_PASSWORD)
            if settings.EMAIL_HOST_PASSWORD else '(empty)'))
        self.stdout.write('DEFAULT_FROM_EMAIL = %s' % settings.DEFAULT_FROM_EMAIL)
        self.stdout.write('SITE_BASE_URL      = %s' % settings.SITE_BASE_URL)
        self.stdout.write('')

        if not settings.EMAIL_ENABLED:
            raise CommandError(
                'EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are empty, so the console\n'
                'backend is active and nothing would actually be delivered.\n'
                'Fill both of them in %s and run this again.' % (settings.PROJECT_DIR / '.env'))

        msg = EmailMultiAlternatives(
            subject='ElectroMart SMTP test',
            body='If you are reading this in your inbox, ElectroMart can send real email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        try:
            msg.send(fail_silently=False)
        except Exception as exc:
            text = str(exc).lower()
            hint = next((h for key, h in HINTS.items() if key in text), None)
            detail = '%s: %s' % (type(exc).__name__, exc)
            if hint:
                detail += '\n\nLikely cause:\n  ' + (
                    hint % (settings.EMAIL_HOST, settings.EMAIL_PORT)
                    if '%s' in hint else hint)
            raise CommandError('Send failed.\n\n  %s' % detail)

        self.stdout.write(self.style.SUCCESS('Sent to %s - check the inbox (and spam).' % to_email))
