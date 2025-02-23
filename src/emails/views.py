from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone

from . import services
from .models import Email, EmailVerificationEvent

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

def reset_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').lower().strip()
        
        try:
            email_obj = Email.objects.get(email=email)
            
            try:
                obj = services.start_verification_event(
                    email,
                    event_type='password_reset'
                )
                messages.success(
                    request,
                    "If an account exists with this email, you'll receive password reset instructions."
                )
                return redirect('login')
                
            except Exception as e:
                print(f"Error sending reset email: {e}")
                messages.error(
                    request,
                    "There was a problem sending the reset email. Please try again later."
                )
                
        except Email.DoesNotExist:
            # Don't reveal whether a user exists
            messages.success(
                request,
                "If an account exists with this email, you'll receive password reset instructions."
            )
            return redirect('login')
            
    return render(request, 'auth/reset_password.html')

def reset_password_confirm_view(request, token):
    try:
        event = EmailVerificationEvent.objects.get(
            token=token,
            event_type='password_reset',
            expired=False
        )
        email_obj = Email.objects.get(email=event.email)
        
    except (EmailVerificationEvent.DoesNotExist, Email.DoesNotExist):
        messages.error(request, "Invalid or expired password reset link.")
        return redirect('login')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validate password
        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'auth/reset_password_confirm.html')
            
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'auth/reset_password_confirm.html')
            
        if not any(c.isupper() for c in password1):
            messages.error(request, "Password must contain at least one uppercase letter.")
            return render(request, 'auth/reset_password_confirm.html')
            
        if not any(c.islower() for c in password1):
            messages.error(request, "Password must contain at least one lowercase letter.")
            return render(request, 'auth/reset_password_confirm.html')
            
        if not any(c.isdigit() for c in password1):
            messages.error(request, "Password must contain at least one number.")
            return render(request, 'auth/reset_password_confirm.html')
            
        # Set new password
        email_obj.set_password(password1)
        email_obj.save()
        
        # Mark event as expired
        event.expired = True
        event.expired_at = timezone.now()
        event.save()
        
        messages.success(request, "Your password has been reset successfully. Please log in with your new password.")
        return redirect('login')
        
    return render(request, 'auth/reset_password_confirm.html')

