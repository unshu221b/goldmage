import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from accounts.models import CustomUser
import json
import hmac
import hashlib
import time

from clerk_backend_api import Clerk
from helpers.myclerk.utils import update_or_create_clerk_user

import logging
logger = logging.getLogger('goldmage')
from svix.webhooks import Webhook, WebhookVerificationError

stripe.api_key = settings.STRIPE_SECRET_KEY

# def verify_clerk_webhook(request, webhook_secret):
#     wh = Webhook(webhook_secret)
#     try:
#         wh.verify(request.body, request.headers)
#         return True
#     except WebhookVerificationError as e:
#         print(f"Svix verification failed: {e}")
#         return False

# @csrf_exempt
# @require_POST
# def clerk_webhook(request):
#     logger.info("Received Clerk webhook request")
#     webhook_secret = settings.CLERK_WEBHOOK_SIGNING_SECRET
#     if not verify_clerk_webhook(request, webhook_secret):
#         logger.error("Invalid webhook signature")
#         return HttpResponse(status=400)
#     try:
#         event_data = json.loads(request.body)
#         event_type = event_data.get('type')
#         logger.info(f"Processing Clerk webhook event: {event_type}")
#         logger.info(f"Event data: {event_data.get('data')}")
#         if event_type == 'user.deleted':
#             clerk_user_id = event_data['data']['id']
#             try:
#                 user = CustomUser.objects.get(clerk_user_id=clerk_user_id)
#                 user.delete()
#                 logger.info(f"Deleted user from webhook: {clerk_user_id}")
#             except CustomUser.DoesNotExist:
#                 logger.info(f"User already deleted: {clerk_user_id}")
#             except Exception as e:
#                 logger.error(f"Error deleting user: {str(e)}", exc_info=True)
#                 return HttpResponse(status=500)
#         elif event_type == 'user.passwordChanged':
#             clerk_user_id = event_data['data']['id']
#             logger.info(f"User password changed: {clerk_user_id}")
#             # Optionally: force logout, notify, or audit here
#         return HttpResponse(status=200)
#     except Exception as e:
#         logger.error(f"Clerk webhook error: {str(e)}", exc_info=True)
#         return HttpResponse(status=400)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    logger.info("Received Stripe webhook request")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Processing Stripe event: {event.type}")
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    try:
        if event.type == 'checkout.session.completed':
            session = event.data.object
            
            # Check if this is a credit purchase (one-time payment)
            if session.metadata.get('purchase_type') == 'credit_purchase':
                try:
                    user = CustomUser.objects.get(id=session.metadata['user_id'])
                    credits_to_add = int(session.metadata['credits'])
                    user.add_credits(credits_to_add)
                    logger.info(f"✅ Added {credits_to_add} credits to user {user.id} (now has {user.credits} credits)")
                    
                    # Track the successful purchase
                    from helpers._mixpanel.client import mixpanel_client
                    mixpanel_client.track_api_event(
                        user_id=user.clerk_user_id,
                        event_name="credit_purchase_completed",
                        properties={
                            "credits_purchased": credits_to_add,
                            "amount_paid": session.amount_total / 100,  # Convert from cents
                            "user_email": user.email,
                            "user_credits_after": user.credits,
                        }
                    )
                except Exception as e:
                    logger.error(f"❌ Error adding credits: {str(e)}", exc_info=True)
            
            # Handle subscription purchases (existing code)
            else:
                try:
                    user = CustomUser.objects.get(clerk_user_id=session.customer)
                    # Set premium membership and credits
                    user.membership = 'PREMIUM'
                    user.credits = 200  # Set initial premium credits
                    user.is_thread_depth_locked = False  # Remove any thread locks
                    user.save()
                    logger.info(f"✅ Premium subscription activated for user {user.id}")
                except CustomUser.DoesNotExist:
                    logger.warning(f"User not found for subscription: {session.customer}")

        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            try:
                user = CustomUser.objects.get(clerk_user_id=subscription.customer)
                # Reset to free tier
                user.membership = 'FREE'
                user.credits = 10  # Reset to free tier credits
                user.save()
            except CustomUser.DoesNotExist:
                pass

        elif event.type in ['customer.subscription.created', 'customer.subscription.updated']:
            subscription = event.data.object
            logger.info(f"New subscription: {event.data.object.id}")
            try:
                user = CustomUser.objects.get(clerk_user_id=subscription.customer)
                if subscription.status == 'active':
                    user.membership = 'PREMIUM'
                else:
                    user.membership = 'FREE'
                user.save()
            except CustomUser.DoesNotExist:
                pass

        elif event.type == 'customer.created':
            customer = event.data.object
            try:
                user = CustomUser.objects.get(clerk_user_id=customer.id)
                user.save()
            except CustomUser.DoesNotExist:
                pass

        elif event.type == 'customer.updated':
            customer = event.data.object
            try:
                user = CustomUser.objects.get(clerk_user_id=customer.id)
                if user.email != customer.email:
                    user.email = customer.email
                    user.save()
            except CustomUser.DoesNotExist:
                pass

        elif event.type == 'customer.deleted':
            customer = event.data.object
            try:
                user = CustomUser.objects.get(clerk_user_id=customer.id)
                user.membership = 'FREE'
                user.save()
            except CustomUser.DoesNotExist:
                pass

        return HttpResponse(status=200)
    
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)