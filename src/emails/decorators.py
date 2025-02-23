from django.core.cache import cache
from django.http import HttpResponseForbidden
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def login_ratelimit(timeout=300, max_attempts=5):  # 5 minutes, 5 attempts
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method == 'POST':
                # Get client IP
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
                email = request.POST.get('email', '').lower().strip()
                
                # Create cache keys
                ip_cache_key = f"login_ip_{ip}"
                email_cache_key = f"login_email_{email}"
                
                # Get current attempts
                ip_attempts = cache.get(ip_cache_key, 0)
                email_attempts = cache.get(email_cache_key, 0)
                
                # Check if max attempts exceeded
                if ip_attempts >= max_attempts or email_attempts >= max_attempts:
                    messages.error(
                        request,
                        f"Too many failed login attempts. Please try again in {timeout//60} minutes."
                    )
                    return redirect('login')
                
                # Only increment if not already at max
                if ip_attempts < max_attempts:
                    cache.set(ip_cache_key, ip_attempts + 1, timeout)
                if email_attempts < max_attempts:
                    cache.set(email_cache_key, email_attempts + 1, timeout)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator 