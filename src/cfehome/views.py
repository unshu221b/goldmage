from django.shortcuts import render, redirect
from helpers.myclerk.decorators import api_login_required
from django.core.mail import send_mail
from django.urls import reverse
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_control
from helpers._mixpanel.client import mixpanel_client

import logging
import stripe
import time
import os
from openai import OpenAI
import json
from django.http import HttpResponse

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
   
@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def create_portal_session(request):
    try:
        for header, value in request.headers.items():
            logger.info(f"{header}: {value}")


        portal_session = stripe.billing_portal.Session.create(
            customer=request.user.clerk_user_id,
            return_url=f"{settings.FRONTEND_URL}/",
        )
        return JsonResponse({'portal_url': portal_session.url})
    except stripe.error.StripeError as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def create_checkout_session(request):
    try:
        # Log authentication details
        logger.info("=== Checkout Session Creation Started ===")
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"User ID: {getattr(request.user, 'id', 'No ID')}")
        logger.info(f"User email: {getattr(request.user, 'email', 'No email')}")
        logger.info(f"User clerk_user_id: {getattr(request.user, 'clerk_user_id', 'No clerk ID')}")
        
        # Log the raw request body
        logger.info(f"Raw request body: {request.body}")
        
        # Log request headers
        logger.info("Request headers:")
        for header, value in request.headers.items():
            logger.info(f"{header}: {value}")

        data = json.loads(request.body)
        period = data.get('period')
        logger.info(f"Requested period: {period}")
        
        # Map the period to the correct Stripe price ID
        price_mapping = {
            'monthly': settings.STRIPE_MONTHLY_PRICE_ID,
            'yearly': settings.STRIPE_YEARLY_PRICE_ID
        }
        price_id = price_mapping.get(period)
        logger.info(f"Selected price ID: {price_id}")

        if not price_id:
            logger.error(f"Invalid period requested: {period}")
            return JsonResponse({'error': 'Invalid period'}, status=400)

        # Create Stripe checkout session with the correct price
        logger.info("Creating Stripe checkout session...")
        checkout_session = stripe.checkout.Session.create(
            # customer=request.user.clerk_user_id,
            customer_email=request.user.email,
            client_reference_id=str(request.user.id),
            metadata={
                'user_id': str(request.user.id),
                'period': period
            },
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/",
        )
        logger.info(f"Checkout session created successfully. URL: {checkout_session.url}")

        mixpanel_client.track_api_event(
            user_id=request.user.clerk_user_id,
            event_name="Checkout Session Created",
            properties={
                "checkout_url": checkout_session.url,
                "period": period,
                "user_email": request.user.email,
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
            }
        )       
             
        return JsonResponse({
            'checkout_url': checkout_session.url
        })
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in create_checkout_session: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=400)

def send_error_email(request, error_code, error_message, stack_trace=None):
    subject = f'52AICHAN Error {error_code}'
    message = f"""
An error occurred on 52AICHAN:

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

