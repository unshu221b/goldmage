from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
import re

from emails import services as emails_services
from emails.models import Email, EmailVerificationEvent
from emails.forms import EmailForm


def login_logout_template_view(request):
    return render(request, "auth/login-logout.html", {})

EMAIL_ADDRESS = settings.EMAIL_ADDRESS
def home_view(request):
    # Redirect to dashboard if authenticated
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    template_name = "home.html"
    context = {
        "form": EmailForm(request.POST or None),
        "message": ""
    }
    
    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid():
            email_val = form.cleaned_data.get('email')
            obj = emails_services.start_verification_event(email_val)
            context['form'] = EmailForm()
            context['message'] = f"Success! Check your email for verification from {EMAIL_ADDRESS}"
    
    return render(request, template_name, context)

@login_required
def dashboard_view(request):
    # No need to redirect for verification now since we show the banner in dashboard
    context = {
        "user": request.user,
    }
    return render(request, "dashboard.html", context)

def login_view(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        try:
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                
                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Expires when browser closes
                
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        except Exception as e:
            messages.error(request, "An error occurred. Please try again.")
            print(e)  # For debugging
    
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def signup_view(request):
    if request.session.get('email_id'):
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        try:
            # Check if email already exists
            if Email.objects.filter(email=email).exists():
                messages.error(request, "Email already registered. Please login.")
                return redirect('login')
            
            # Validate passwords match
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'auth/signup.html')
            
            # Validate password requirements
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return render(request, 'auth/signup.html')
            
            if not re.search(r'[A-Z]', password):
                messages.error(request, "Password must contain at least one uppercase letter.")
                return render(request, 'auth/signup.html')
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                messages.error(request, "Password must contain at least one special character.")
                return render(request, 'auth/signup.html')
            
            # Create new user
            user = Email.objects.create_user(email=email, password=password)
            
            # Start verification process
            obj = emails_services.start_verification_event(email)
            messages.success(request, f"Success! Check your email for verification from {settings.EMAIL_ADDRESS}")
            return redirect('login')
            
        except Exception as e:
            messages.error(request, "An error occurred. Please try again.")
            print(e)  # For debugging
    
    return render(request, 'auth/signup.html')