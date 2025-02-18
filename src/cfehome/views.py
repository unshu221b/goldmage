from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
import re
from django.urls import reverse
from django.http import JsonResponse

from emails import services as emails_services
from emails.models import Email, EmailVerificationEvent
from emails.forms import EmailForm
from courses.models import Course, Lesson, PublishStatus

import stripe
# This is your test secret API key.
stripe.api_key = settings.STRIPE_SECRET_KEY


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
    # Get courses and continue watching with progress
    courses = Course.objects.all()
    
    # Get lessons with watch progress
    continue_watching = Lesson.objects.filter(
        watchprogress__user=request.user,
        watchprogress__current_time__gt=0,
        status=PublishStatus.PUBLISHED
    ).order_by('-watchprogress__last_watched')[:10]  # Get 10 items for 2 slides of 5

    # If no watched lessons, show latest published lessons
    if not continue_watching:
        continue_watching = Lesson.objects.filter(
            status=PublishStatus.PUBLISHED
        ).order_by('-updated')[:10]
    
    # Check if request is from mobile
    is_mobile = request.user_agent.is_mobile if hasattr(request, 'user_agent') else False
    
    context = {
        'continue_watching': continue_watching,
        'courses': courses,
        'is_mobile': is_mobile,
    }
    return render(request, 'dashboard.html', context)

@login_required
def settings_view(request):
    context = {
        'user': request.user,
        'account_type': request.user.account_type,
    }
    
    # Only try to create billing portal if user has a customer_id
    if hasattr(request.user, 'customer_id') and request.user.customer_id:
        try:
            session = stripe.billing_portal.Session.create(
                customer=request.user.customer_id,
                return_url=request.build_absolute_uri(reverse('settings')),
            )
        except stripe.error.StripeError as e:
            # Handle any other Stripe errors
            print(f"Stripe error: {str(e)}")
    
    return render(request, 'settings.html', context)


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
            
            # Log the user in
            login(request, user)
            
            # Redirect to payment page instead of login
            return redirect('payment_checkout')
            
        except Exception as e:
            messages.error(request, "An error occurred. Please try again.")
            print(e)
    
    return render(request, 'auth/signup.html')

# New view for payment
def payment_checkout(request):
    if not request.user.is_authenticated:
        return redirect('signup')
        
    if request.method == 'POST':
        try:
            session = stripe.checkout.Session.create(
                ui_mode='embedded',
                line_items=[{
                    'price': settings.STRIPE_PRO_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                locale='zh-HK',  # Set language to Chinese
                customer_email=request.user.email,  # Pre-fill customer email
                return_url=request.build_absolute_uri(
                    reverse('payment_return')
                ) + '?session_id={CHECKOUT_SESSION_ID}',
            )
            print("Session created:", session)
            print("Client Secret:", session.client_secret)
            return JsonResponse({'clientSecret': session.client_secret})
            
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({'error': str(e)}, status=400)
    
    return render(request, 'payment/checkout.html', {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    })

def payment_return(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            # Retrieve the session from Stripe
            session = stripe.checkout.Session.retrieve(session_id)
            if session.status == 'complete':
                return render(request, 'payment/success.html', {
                    'customer_email': session.customer_email
                })
            # If the session is not complete, you can choose to do nothing
            # since Stripe handles the error messages in the embedded form
        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error retrieving session: {e}")
            # Optionally, you can handle the error here if needed
    
    # No need to redirect; let the user stay on the current page

    
@login_required
def create_portal_session(request):
    if not request.user.customer_id:
        return JsonResponse({'error': 'No customer ID found'}, status=400)
        
    try:
        # Create portal session with minimal configuration
        session = stripe.billing_portal.Session.create(
            customer=request.user.customer_id,
            return_url=request.build_absolute_uri(reverse('settings')),
        )
        return JsonResponse({'url': session.url})
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@login_required
def create_checkout_session(request):
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.customer_id,  # Optional - for existing customers
            client_reference_id=request.user.id,  # To link the session to your user
            mode='subscription',
            line_items=[{
                'price': settings.STRIPE_PRO_PRICE_ID,  # Your price ID from Stripe
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri(reverse('dashboard')) + '?success=true',
            cancel_url=request.build_absolute_uri(reverse('settings')) + '?canceled=true',
        )
        return JsonResponse({'url': checkout_session.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)