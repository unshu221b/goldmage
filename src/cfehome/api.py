import os
import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import authenticate_request, AuthenticateRequestOptions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.conf import settings
from django.http import JsonResponse

def is_signed_in(request: httpx.Request):
    sdk = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
    request_state = sdk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=settings.BASE_CSRF_TRUSTED_ORIGINS
        )
    )
    return request_state.is_signed_in

@api_view(['GET'])
def user_summary(request):
    # Example data (replace with your actual logic)
    data = {
        "username": request.user.username,
        "email": request.user.email,
        "subscription_status": "active",
        "usage": {
            "requests_this_month": 42,
            "plan_limit": 100
        }
    }
    return Response(data)