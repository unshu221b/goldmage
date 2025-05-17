from django.shortcuts import render, redirect
from helpers.myclerk.decorators import api_login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.db.models import Q
from django.views.decorators.cache import cache_control

from itertools import chain
from courses.models import Course, Lesson, PublishStatus, WatchProgress
import traceback
import logging
import stripe
import time
import os
from openai import OpenAI
import json

logger = logging.getLogger('goldmage')
stripe.api_key = settings.STRIPE_SECRET_KEY
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def monitor_cache_stats(view_name):
    """
    Track cache hits and misses for performance monitoring
    """
    stats_key = f'cache_stats_{view_name}'
    stats = cache.get(stats_key, {'hits': 0, 'misses': 0})
    
    def update_stats(hit=True):
        if hit:
            stats['hits'] += 1
        else:
            stats['misses'] += 1
        cache.set(stats_key, stats)
        
        # Log the stats periodically (every 100 hits)
        total = stats['hits'] + stats['misses']
        if total % 100 == 0:
            hit_rate = (stats['hits'] / total) * 100
            logger.info(f"Cache stats for {view_name}: "
                       f"Hit rate: {hit_rate:.1f}%, "
                       f"Hits: {stats['hits']}, "
                       f"Misses: {stats['misses']}")
    
    return stats, update_stats

EMAIL_ADDRESS = settings.EMAIL_ADDRESS
@cache_control(max_age=3600, public=True)  # 1 hour
def home_view(request):
 
    template_name = "home.html"

    return render(request, template_name)


@cache_control(private=True, max_age=300)  # 5 minutes
@api_login_required
def dashboard_view(request):
    start_time = time.time()
    stats, update_stats = monitor_cache_stats('dashboard')

    user_id = request.user.id
    watch_cache_key = f'user_{user_id}_watch_history'
    recent_cache_key = f'user_{user_id}_recent_lessons'
    suggested_cache_key = f'user_{user_id}_suggested'
    featured_cache_key = 'featured_lessons'  # This can be shared across users
    
    # Try to get watched videos from cache
    watched_videos = cache.get(watch_cache_key)
    if watched_videos is None:
        update_stats(hit=False)  # Cache miss
        watched_videos = WatchProgress.objects.filter(
            user=request.user
        ).select_related('lesson').order_by('-last_watched')[:10]
        cache_success = cache.set(watch_cache_key, list(watched_videos), 300)
    else:
        update_stats(hit=True)  # Cache hit
    
    # Try to get recent lessons from cache
    recent_lessons = cache.get(recent_cache_key)
    if recent_lessons is None:
        update_stats(hit=False)  # Cache miss
        recent_lessons = Lesson.objects.filter(
            status=PublishStatus.PUBLISHED,
            course__status=PublishStatus.PUBLISHED
        ).exclude(
            watchprogress__user=request.user
        ).order_by('-updated')[:6]
        cache.set(recent_cache_key, recent_lessons, 900)
    else:
        update_stats(hit=True)  # Cache hit
    
    # Combine for continue watching
    continue_watching = list(chain(watched_videos, recent_lessons))[:10]
    
    # Try to get suggested lessons from cache
    suggested_lessons = cache.get(suggested_cache_key)
    if suggested_lessons is None:
        update_stats(hit=False)  # Cache miss
        suggested_lessons = Lesson.get_suggested(user=request.user)[:15]
        cache.set(suggested_cache_key, suggested_lessons, 600)
    else:
        update_stats(hit=True)  # Cache hit
    
    # Try to get featured lessons from cache
    featured_lessons = cache.get(featured_cache_key)
    if featured_lessons is None:
        update_stats(hit=False)  # Cache miss
        featured_lessons = Lesson.get_featured()
        cache.set(featured_cache_key, featured_lessons, 3600)
    else:
        update_stats(hit=True)  # Cache hit
    
    context = {
        'continue_watching': continue_watching,
        'featured_lessons': featured_lessons,
        'suggested_lessons': suggested_lessons,
    }
    end_time = time.time()
    duration = end_time - start_time
    print(f"Dashboard view took {duration:.2f} seconds")
    return render(request, 'dashboard.html', context)


@ensure_csrf_cookie
@csrf_protect
@api_login_required
def product_page(request):
    return render(request, 'product.html')

@ensure_csrf_cookie
@csrf_protect
@api_login_required
def analyze_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            messages = data.get("messages", [])
            # Combine messages into a single string for analysis
            user_message = messages[-1]["text"] if messages else ""

            # Build the prompt
            prompt = (
                "Analyze the following chat message and generate a reaction and 4 different response suggestions. "
                "Return a JSON object with these fields:\n"
                "{\n"
                '  "reaction": "A brief emotional reaction to the message",\n'
                '  "suggestions": [\n'
                '    {\n'
                '      "faceSrc": "/static/52aichan.png",\n'
                '      "suggestion": "first suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "faceSrc": "/static/52aichan.png",\n'
                '      "suggestion": "second suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "faceSrc": "/static/52aichan.png",\n'
                '      "suggestion": "third suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "faceSrc": "/static/52aichan.png",\n'
                '      "suggestion": "fourth suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    }\n'
                '  ],\n'
                '  "metrics": {\n'
                '    "intelligence": number between 0-100,\n'
                '    "charisma": number between 0-100,\n'
                '    "strength": number between 0-100,\n'
                '    "kindness": number between 0-100\n'
                '  }\n'
                "}\n\n"
                f"Message: \"{user_message}\""
            )

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert communication analyst and response generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
                temperature=0.7,
            )
            ai_content = response.choices[0].message.content.strip()

            # Try to parse the JSON from the AI's response
            try:
                openai_result = json.loads(ai_content)
            except json.JSONDecodeError:
                # Fallback: try to extract JSON from the response text
                import re
                match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if match:
                    openai_result = json.loads(match.group(0))
                else:
                    return JsonResponse({"error": "AI response was not valid JSON", "raw": ai_content}, status=500)

            # Build the response structure
            response_data = {
                "reaction": openai_result.get("reaction", ""),
                "suggestions": openai_result.get("suggestions", []),
                "metrics": openai_result.get("metrics", {
                    "intelligence": 50,
                    "charisma": 50,
                    "strength": 50,
                    "kindness": 50
                })
            }
            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)


@api_login_required
def continue_watching_all_view(request):
    # Get recently watched videos with related lesson data
    watched_videos = WatchProgress.objects.filter(
        user=request.user
    ).select_related('lesson', 'lesson__course').order_by('-last_watched')
    
    context = {
        'continue_watching': watched_videos,
        'title': 'Continue Watching'
    }
    return render(request, 'courses/continue_watching_all.html', context)

@api_login_required
def featured_content_all_view(request):
    # Get recently watched videos with related lesson data
    featured_lessons = Lesson.get_featured()
    
    context = {
        'featured_lessons': featured_lessons,
        'title': 'Featured Content'
    }
    return render(request, 'courses/featured_content_all.html', context)

@api_login_required
def suggested_content_all_view(request):
    suggested_lessons = Lesson.get_suggested(user=request.user)
    
    context = {
        'suggested_lessons': suggested_lessons,
        'title': 'Suggested Content'
    }
    return render(request, 'courses/suggested_content_all.html', context)

@api_login_required
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

@api_login_required
def history_view(request):
    # Get watch history ordered by most recently watched
    watch_history = WatchProgress.objects.filter(
        user=request.user
    ).select_related(
        'lesson', 
        'lesson__course'
    ).order_by(
        '-last_watched'
    )

    context = {
        'watch_history': watch_history,
        'show_footer': False  # Hide footer for scrollable content
    }
    return render(request, 'history.html', context)

@api_login_required
def liked_videos_view(request):
    # Get all lessons liked by the user
    liked_videos = Lesson.objects.filter(
        lesson_likes__user=request.user
    ).select_related('course').order_by('-lesson_likes__created_at')

    context = {
        'liked_videos': liked_videos,
        'show_footer': False  # Add this flag
    }
    return render(request, 'liked_videos.html', context)

@api_login_required
def search_view(request):
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # Search in title and description fields
        # Only show published lessons from published courses
        results = Lesson.objects.filter(
            Q(title__icontains=query) |  # Case-insensitive search in title
            Q(description__icontains=query),  # Case-insensitive search in description
            status=PublishStatus.PUBLISHED,  # Only published lessons
            course__status=PublishStatus.PUBLISHED  # From published courses
        ).select_related('course').distinct()  # Include course data and remove duplicates
    
    context = {
        'query': query,
        'results': results
    }
    return render(request, 'search.html', context)

@cache_control(public=True, max_age=86400)  # 24 hours
def help_view(request):
    return render(request, 'help.html')  # Just render the template

@ensure_csrf_cookie
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
                locale='zh-HK',
                customer=request.user.clerk_user_id,  # Use Clerk ID as Stripe customer ID
                return_url=request.build_absolute_uri(
                    reverse('payment_return')
                ) + '?session_id={CHECKOUT_SESSION_ID}',
            )
            
            return JsonResponse({'clientSecret': session.client_secret})
            
        except Exception as e:
            logger.error(f"Payment error occurred", exc_info=True)
            return JsonResponse({'error': 'Unable to process payment'}, status=400)
    
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

    
@api_login_required
def create_portal_session(request):
    try:
        session = stripe.billing_portal.Session.create(
            customer=request.user.clerk_user_id,  # Use Clerk ID
            return_url=request.build_absolute_uri(reverse('settings')),
        )
        return JsonResponse({'url': session.url})
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)
    
@api_login_required
@ensure_csrf_cookie
def create_checkout_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=request.user.clerk_user_id,  # Use Clerk ID
            client_reference_id=request.user.id,
            mode='subscription',
            line_items=[{
                'price': settings.STRIPE_PRO_PRICE_ID,
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri(reverse('dashboard')) + '?success=true',
            cancel_url=request.build_absolute_uri(reverse('settings')) + '?canceled=true',
        )
        return JsonResponse({'url': checkout_session.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def send_error_email(request, error_code, error_message, stack_trace=None):
    subject = f'Goldmage Error {error_code}'
    message = f"""
An error occurred on Goldmage:

Error Code: {error_code}
Error Message: {error_message}
Path: {request.path}
Method: {request.method}
User: {request.user}

Stack Trace:
{stack_trace if stack_trace else 'No stack trace available'}
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL],
        fail_silently=True,
    )

def handler404(request, exception):
    error_message = "Page not found"
    send_error_email(request, 404, error_message)
    return render(request, 'error.html', {
        'error_code': '404',
        'error_message': error_message
    }, status=404)

def handler500(request):
    error_message = "Internal server error"
    stack_trace = traceback.format_exc()
    send_error_email(request, 500, error_message, stack_trace)
    return render(request, 'error.html', {
        'error_code': '500',
        'error_message': error_message
    }, status=500)

# Add cache invalidation functions
def invalidate_user_cache(user_id):
    """Call this when user data needs to be refreshed"""
    cache.delete(f'user_{user_id}_watch_history')
    cache.delete(f'user_{user_id}_recent_lessons')
    cache.delete(f'user_{user_id}_suggested')

def invalidate_featured_cache():
    """Call this when featured content changes"""
    cache.delete('featured_lessons')