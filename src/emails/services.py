from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import Email, EmailVerificationEvent
from django.template.loader import render_to_string
import uuid
import logging

EMAIL_HOST_USER = settings.EMAIL_HOST_USER

def verify_email(email):
    qs = Email.objects.filter(email=email, active=False)
    return qs.exists()

def start_verification_event(email, event_type='registration', metadata=None):
    """
    Start email verification process
    """
    logger = logging.getLogger('goldmage')
    logger.info(f"Starting {event_type} verification for: {email}")
    try:
        token = uuid.uuid4()
        
        # Generate appropriate URL based on event type
        if event_type == 'registration':
            url = f"{settings.BASE_URL}/verify/{token}/"
        elif event_type == 'password_reset':
            url = f"{settings.BASE_URL}/reset-password/confirm/{token}/"
        
        # Update metadata with URL
        metadata = metadata or {}
        metadata.update({
            'verify_url': url if event_type == 'registration' else None,
            'reset_url': url if event_type == 'password_reset' else None
        })
        
        # Create verification event
        event = EmailVerificationEvent.objects.create(
            email=email,
            token=token,
            event_type=event_type,
            metadata=metadata
        )

        # Get the appropriate template and subject
        if event_type == 'registration':
            template_name = 'emails/verification.html'
            subject = 'Verify your email address'
        elif event_type == 'password_reset':
            template_name = 'emails/password_reset.html'
            subject = 'Reset your password'

        # Render email template
        html_content = render_to_string(template_name, {
            'token': token,
            'metadata': metadata,
            'email': email,
        })

        # Send email
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_content
        )

        logger.info(f"Verification email sent successfully to: {email}")
        return event
    except Exception as e:
        logger.error(f"Verification email failed: {str(e)}", exc_info=True)

def verify_token(token, max_attempts=5):
    qs = EmailVerificationEvent.objects.filter(token=token)
    if not qs.exists() and not qs.count() == 1:
        return False, "Invalid token", None
    """
    Has token
    """
    has_email_expired = qs.filter(expired=True)
    if has_email_expired.exists():
        """ token exipred"""
        return False, "Token expired, try again.", None
    """
    Has token, not expired
    """
    max_attempts_reached = qs.filter(attempts__gte=max_attempts)
    if max_attempts_reached.exists():
        """ update max attempts + 1"""
        # max_tempts_reached.update()
        return False, "Token expired, used too many times", None
    """Token valid"""
    """ update attempts, expire token if attempts > max"""
    obj = qs.first()
    obj.attempts += 1
    obj.last_attempt_at = timezone.now()
    if obj.attempts > max_attempts:
        """invalidation process"""
        obj.expired = True
        obj.expired_at = timezone.now()
    obj.save()
    email_obj = obj.parent # Email.objects.get()
    return True, "Welcome", email_obj