"""Shared email module (Viec 10 / CV59).

One place to send every email the site needs, built on top of Django's own
mail machinery (django.core.mail) - SMTP settings live in settings.py /
.env. Handed off to the rest of the team: Tin's order module and Minh's
feedback module can call send_mail() directly with their own HTML
template, they do not need to duplicate any of this.

In development (no EMAIL_HOST_USER configured) Django's EMAIL_BACKEND is
set to the console backend in settings.py, so "sending" an email just
prints it to the terminal instead of needing a real Gmail app password -
useful for testing the flow before demo day.
"""
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger('accounts.mailer')


def send_mail(to_email, subject, template_name, context=None):
    """Render Frontend/templates/emails/<template_name> and send it.

    Returns True/False instead of raising, so a caller (e.g. register())
    can still finish the request and show a friendly message even if the
    SMTP server is unreachable - the user account is not lost just because
    an email failed to go out.
    """
    context = context or {}
    html_body = render_to_string('emails/%s' % template_name, context)
    ok = True
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=html_body,  # plain-text fallback: the HTML itself is readable enough
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
    except Exception:
        ok = False
        logger.exception('Failed to send "%s" to %s', subject, to_email)

    # CV59 step 3: log every email attempt for debugging, success or not.
    logger.info('%s | to=%s | subject=%s | template=%s',
                'SENT' if ok else 'FAILED', to_email, subject, template_name)
    return ok


def send_activation_email(user, token):
    activate_url = '%s/accounts/activate/%s/' % (settings.SITE_BASE_URL, token)
    return send_mail(
        user['email'],
        'Activate your ElectroMart account',
        'activation_email.html',
        {'full_name': user['full_name'], 'activate_url': activate_url},
    )


def send_password_reset_email(user, token):
    reset_url = '%s/accounts/reset-password/%s/' % (settings.SITE_BASE_URL, token)
    return send_mail(
        user['email'],
        'Reset your ElectroMart password',
        'activation_email.html',  # same simple layout, different context below
        {'full_name': user['full_name'], 'activate_url': reset_url,
         'is_reset': True},
    )


def send_b2b_approval_email(user, approved, reason=''):
    return send_mail(
        user['email'],
        'Your business account has been approved' if approved
        else 'Your business account application was not approved',
        'b2b_approval_email.html',
        {'full_name': user['full_name'], 'approved': approved, 'reason': reason},
    )
