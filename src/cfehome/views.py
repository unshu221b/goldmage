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


@csrf_exempt
def cors_test(request):
    response = HttpResponse("CORS is working!")
    response["Access-Control-Allow-Origin"] = "https://www.52aichan.com"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response



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
                "Analyze the following chat message and generate a reaction, suggestions, and metrics. "
                "Return a JSON object with these fields:\n"
                "{\n"
                '  "reaction": "A brief emotional reaction to the message",\n'
                '  "suggestions": [\n'
                '    {\n'
                '      "id": "unique-id-1",\n'
                '      "suggestion": "first suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-2",\n'
                '      "suggestion": "second suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-3",\n'
                '      "suggestion": "third suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-4",\n'
                '      "suggestion": "fourth suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    }\n'
                '  ],\n'
                '  "personality_metrics": {\n'
                '    "intelligence": number between 0-100 or null,\n'
                '    "charisma": number between 0-100 or null,\n'
                '    "strength": number between 0-100 or null,\n'
                '    "kindness": number between 0-100 or null\n'
                '  },\n'
                '  "emotion_metrics": {\n'
                '    "happiness": number between 0-100,\n'
                '    "sadness": number between 0-100,\n'
                '    "anger": number between 0-100,\n'
                '    "surprise": number between 0-100,\n'
                '    "fear": number between 0-100,\n'
                '    "disgust": number between 0-100,\n'
                '    "neutral": number between 0-100\n'
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
                "personality_metrics": openai_result.get("personality_metrics", {
                    "intelligence": None,
                    "charisma": None,
                    "strength": None,
                    "kindness": None
                }),
                "emotion_metrics": openai_result.get("emotion_metrics", {
                    "happiness": 50,
                    "sadness": 50,
                    "anger": 50,
                    "surprise": 50,
                    "fear": 50,
                    "disgust": 50,
                    "neutral": 50
                })
            }
            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)



    
@csrf_exempt
@api_login_required
@require_http_methods(["POST"])
def create_portal_session(request):
    try:
        for header, value in request.headers.items():
            logger.info(f"{header}: {value}")


        portal_session = stripe.billing_portal.Session.create(
            customer=request.user.clerk_user_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard",
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
            cancel_url=f"{settings.FRONTEND_URL}/dashboard",
        )
        logger.info(f"Checkout session created successfully. URL: {checkout_session.url}")
            
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

