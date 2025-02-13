import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from emails.models import Email

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # Handle the event
    try:
        if event.type == 'checkout.session.completed':
            session = event.data.object
            # Link customer_id to user
            try:
                user = Email.objects.get(email=session.customer_details.email)
                user.customer_id = session.customer
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            customer_id = subscription.customer
            
            try:
                user = Email.objects.get(customer_id=customer_id)
                user.account_type = 'FREE'
                user.save()
            except Email.DoesNotExist:
                pass

        elif event.type in ['customer.subscription.created', 'customer.subscription.updated']:
            subscription = event.data.object
            customer_id = subscription.customer
            
            try:
                user = Email.objects.get(customer_id=customer_id)
                if subscription.status == 'active':
                    if subscription.cancel_at_period_end:
                        pass
                    user.account_type = 'PRO'
                else:
                    user.account_type = 'FREE'
                user.save()
            except Email.DoesNotExist:
                pass

        return HttpResponse(status=200)
    
    except Exception:
        return HttpResponse(status=400)