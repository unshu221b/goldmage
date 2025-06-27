from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import traceback
from django.core.mail import send_mail
from django.conf import settings
from .views import send_error_email

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated and not request.user.is_superuser:
                messages.error(request, "You don't have permission to access the admin area.")
                return redirect('/')  # or wherever you want to redirect
        return self.get_response(request)

class ErrorNotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Only send emails for 500 errors
        if hasattr(exception, 'status_code') and exception.status_code == 500:
            send_error_email(
                request, 
                "500", 
                str(exception), 
                traceback.format_exc()
            )
        return None