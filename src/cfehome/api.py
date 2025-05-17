import os
import httpx
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import authenticate_request, AuthenticateRequestOptions
from rest_framework.decorators import api_view
from rest_framework.response import Response

from helpers import myclerk
from django.conf import settings
from django.http import JsonResponse


@myclerk.api_login_required
def user_summary(request):
    user = request.user
    return JsonResponse({"first_name": user.first_name, "id": user.id})