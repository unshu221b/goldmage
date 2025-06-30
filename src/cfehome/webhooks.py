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

stripe.api_key = settings.STRIPE_SECRET_KEY

def verify_clerk_webhook(request, webhook_secret):
    """Verify Clerk webhook signature using HMAC"""
    signature = request.headers.get('svix-signature')
    timestamp = request.headers.get('svix-timestamp')
    webhook_id = request.headers.get('svix-id')
    
    if not all([signature, timestamp, webhook_id]):
        return False
        
    # Verify timestamp is within 5 minutes
    current_time = int(time.time())
    timestamp_int = int(timestamp)
    if abs(current_time - timestamp_int) > 300:  # 5 minutes
        return False
        
    # Create the signature string
    signature_string = f"{webhook_id}.{timestamp}.{request.body.decode('utf-8')}"
    
    # Create HMAC
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature, expected_signature)

@csrf_exempt
@require_POST
def clerk_webhook(request):
    logger.info("Received Clerk webhook request")
    
    # Get the webhook secret from settings
    webhook_secret = settings.CLERK_WEBHOOK_SIGNING_SECRET
    
    # Verify the webhook
    if not verify_clerk_webhook(request, webhook_secret):
        logger.error("Invalid webhook signature")
        return HttpResponse(status=400)
    
    try:
        # Parse the payload
        event_data = json.loads(request.body)
        
        logger.info(f"Processing Clerk webhook event: {event_data.get('type')}")
        logger.info(f"Event data: {event_data.get('data')}")
        
        # Handle different event types
        if event_data.get('type') == 'user.created':
            # Create user in Django database
            clerk_user_id = event_data['data']['id']
            
            # Get primary email from email_addresses array
            primary_email = None
            if event_data['data'].get('email_addresses'):
                for email in event_data['data']['email_addresses']:
                    if email['id'] == event_data['data'].get('primary_email_address_id'):
                        primary_email = email['email_address']
                        break
            
            # Get name from external accounts if available
            first_name = event_data['data'].get('first_name')
            last_name = event_data['data'].get('last_name')
            
            if event_data['data'].get('external_accounts'):
                external_account = event_data['data']['external_accounts'][0]
                if not first_name and external_account.get('first_name'):
                    first_name = external_account['first_name']
                if not last_name and external_account.get('last_name'):
                    last_name = external_account['last_name']
            
            user_data = {
                "username": event_data['data'].get('username') or f"user_{clerk_user_id[-8:]}",
                "first_name": first_name or "",
                "last_name": last_name or "",
                "email": primary_email or "",
                "membership": "free",  # Default to free membership
                "credits": 10  # Add initial free credits
            }
            
            logger.info(f"Creating user with data: {user_data}")
            
            try:
                user, created = CustomUser.objects.update_or_create(
                    clerk_user_id=clerk_user_id,
                    defaults=user_data
                )
                if created:
                    logger.info(f"Created new user from webhook: {clerk_user_id} with {user.credits} credits")
                else:
                    logger.info(f"Updated existing user from webhook: {clerk_user_id}")
            except Exception as e:
                logger.error(f"Error creating/updating user: {str(e)}", exc_info=True)
                return HttpResponse(status=500)
                
        elif event_data.get('type') == 'user.updated':
            # Update user in Django database
            clerk_user_id = event_data['data']['id']
            
            # Get primary email from email_addresses array
            primary_email = None
            if event_data['data'].get('email_addresses'):
                for email in event_data['data']['email_addresses']:
                    if email['id'] == event_data['data'].get('primary_email_address_id'):
                        primary_email = email['email_address']
                        break
            
            # Get name from external accounts if available
            first_name = event_data['data'].get('first_name')
            last_name = event_data['data'].get('last_name')
            
            if event_data['data'].get('external_accounts'):
                external_account = event_data['data']['external_accounts'][0]
                if not first_name and external_account.get('first_name'):
                    first_name = external_account['first_name']
                if not last_name and external_account.get('last_name'):
                    last_name = external_account['last_name']
            
            user_data = {
                "username": event_data['data'].get('username') or f"user_{clerk_user_id[-8:]}",
                "first_name": first_name or "",
                "last_name": last_name or "",
                "email": primary_email or "",
            }
            
            logger.info(f"Updating user with data: {user_data}")
            
            try:
                user, created = CustomUser.objects.update_or_create(
                    clerk_user_id=clerk_user_id,
                    defaults=user_data
                )
                logger.info(f"Updated user from webhook: {clerk_user_id}")
            except Exception as e:
                logger.error(f"Error updating user: {str(e)}", exc_info=True)
                return HttpResponse(status=500)
            
        elif event_data.get('type') == 'user.deleted':
            # Handle user deletion if needed
            clerk_user_id = event_data['data']['id']
            try:
                user = CustomUser.objects.get(clerk_user_id=clerk_user_id)
                user.delete()
                logger.info(f"Deleted user from webhook: {clerk_user_id}")
            except CustomUser.DoesNotExist:
                logger.info(f"User already deleted: {clerk_user_id}")
            except Exception as e:
                logger.error(f"Error deleting user: {str(e)}", exc_info=True)
                return HttpResponse(status=500)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Clerk webhook error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)

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
                    user.membership = 'premium'
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
                user.membership = 'free'
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
                    user.membership = 'premium'
                else:
                    user.membership = 'free'
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
                user.membership = 'free'
                user.save()
            except CustomUser.DoesNotExist:
                pass

        return HttpResponse(status=200)
    
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)