from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import JsonResponse

from . import services
from .models import Email

EMAIL_ADDRESS = settings.EMAIL_ADDRESS

def verify_email_token_view(request, token, *args, **kwargs):
    did_verify, msg, email_obj = services.verify_token(token)
    if not did_verify:
        messages.error(request, msg)
        return redirect("/login/")
    
    # Update user verification status
    email_obj.is_verified = True
    email_obj.save()
    
    # Log the user in
    login(request, email_obj)
    messages.success(request, msg)
    
    next_url = request.session.get('next_url') or "/"
    if not next_url.startswith("/"):
        next_url = "/"
    return redirect(next_url)

def resend_verification_email(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            # Start new verification process
            obj = services.start_verification_event(request.user.email)
            return JsonResponse({
                'status': 'success',
                'message': f'Verification email sent to {request.user.email}'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to send verification email. Please try again.'
            }, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)