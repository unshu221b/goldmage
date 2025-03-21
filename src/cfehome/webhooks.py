import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from emails.models import Email
import logging
logger = logging.getLogger('goldmage')

stripe.api_key = settings.STRIPE_SECRET_KEY

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
            try:
                user = Email.objects.get(email=session.customer_details.email)
                user.customer_id = session.customer
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            try:
                user = Email.objects.get(customer_id=subscription.customer)
                user.account_type = 'FREE'
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type in ['customer.subscription.created', 'customer.subscription.updated']:
            subscription = event.data.object
            logger.info(f"New subscription: {event.data.object.id}")
            try:
                user = Email.objects.get(customer_id=subscription.customer)
                if subscription.status == 'active':
                    user.account_type = 'PRO'
                else:
                    user.account_type = 'FREE'
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type == 'customer.created':
            customer = event.data.object
            try:
                user = Email.objects.get(email=customer.email)
                user.customer_id = customer.id
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type == 'customer.updated':
            customer = event.data.object
            try:
                user = Email.objects.get(customer_id=customer.id)
                if user.email != customer.email:
                    user.email = customer.email
                    user.save()
            except Email.DoesNotExist:
                pass

        elif event.type == 'customer.deleted':
            customer = event.data.object
            try:
                user = Email.objects.get(customer_id=customer.id)
                user.customer_id = None
                user.account_type = 'FREE'
                user.save()
            except Email.DoesNotExist:
                pass

        return HttpResponse(status=200)
    
    except Exception:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)