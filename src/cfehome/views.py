from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
import re
from django.urls import reverse
from django.http import JsonResponse
from itertools import chain
from django.db.models import Count, Q
import random

from emails import services as emails_services
from emails.models import Email, EmailVerificationEvent
from emails.forms import EmailForm
from courses.models import Course, Lesson, PublishStatus, WatchProgress

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
    
    # Get recently watched videos
    watched_videos = WatchProgress.objects.filter(
        user=request.user
    ).select_related('lesson').order_by('-last_watched')[:6]
    
    # Get recent published lessons not in watch history
    recent_lessons = Lesson.objects.filter(
        status=PublishStatus.PUBLISHED,
        course__status=PublishStatus.PUBLISHED
    ).exclude(
        watchprogress__user=request.user  # Exclude watched lessons
    ).order_by('-updated')[:10]
    
    # Combine both querysets
    continue_watching = list(chain(watched_videos, recent_lessons))[:10]  # Ensure we have up to 10 items

    #########################################################
    # Base queryset for all published lessons
    suggested_base = Lesson.objects.filter(
        status=PublishStatus.PUBLISHED,
        course__status=PublishStatus.PUBLISHED
    ).select_related('course').exclude(
        watchprogress__user=request.user  # Exclude all watched lessons upfront
    )
    
    # 1. Get lessons from courses user has watched (up to 5)
    watched_course_lessons = suggested_base.filter(
        course__lesson__watchprogress__user=request.user
    ).distinct()[:5]
    
    # 2. Get popular lessons, excluding ones from watched courses (up to 3)
    popular_lessons = suggested_base.exclude(
        id__in=watched_course_lessons.values_list('id', flat=True)
    ).annotate(
        watch_count=Count('watchprogress')
    ).filter(watch_count__gt=0).order_by('-watch_count')[:6]
    
    # 3. Get latest lessons, excluding both above sets (up to 4)
    latest_lessons = suggested_base.exclude(
        id__in=list(chain(
            watched_course_lessons.values_list('id', flat=True),
            popular_lessons.values_list('id', flat=True)
        ))
    ).order_by('-updated')[:4]
    
    # Combine all sources
    suggested_lessons = list(chain(
        watched_course_lessons,
        popular_lessons,
        latest_lessons
    ))

    # Shuffle the final list
    random.shuffle(suggested_lessons)
    
    context = {
        'continue_watching': continue_watching,
        'featured_lessons': Lesson.get_featured(),
        'suggested_lessons': suggested_lessons,
    }
    return render(request, 'dashboard.html', context)

@login_required
def continue_watching_all_view(request):
    # Get recently watched videos with related lesson data
    watched_videos = WatchProgress.objects.filter(
        user=request.user
    ).select_related('lesson', 'lesson__course').order_by('-last_watched')
    
    context = {
        'continue_watching': watched_videos,
        'title': 'Continue Watching'
    }
    return render(request, 'continue_watching_all.html', context)

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

@login_required
def history_view(request):
    return render(request, 'history.html')

@login_required
def liked_videos_view(request):
    return render(request, 'liked_videos.html')

@login_required
def help_view(request):
    return render(request, 'help.html')

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