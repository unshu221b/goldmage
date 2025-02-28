from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if request.user.is_authenticated and not request.user.is_superuser:
                messages.error(request, "You don't have permission to access the admin area.")
                return redirect('dashboard')  # or wherever you want to redirect
        return self.get_response(request) 