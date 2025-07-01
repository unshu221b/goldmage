import os
import httpx
from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging

from helpers import myclerk
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('goldmage')

@myclerk.api_login_required
def user_summary(request):
    try:
        if not request.user.is_authenticated:
            logger.warning("User not authenticated in user_summary view")
            return JsonResponse({"detail": "Authentication required"}, status=401)
            
        user = request.user
        logger.info(f"User summary requested for user: {user.clerk_user_id}")
        
        return JsonResponse({
            "first_name": user.first_name,
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email
        })
    except Exception as e:
        logger.error(f"Error in user_summary view: {str(e)}", exc_info=True)
        return JsonResponse({"detail": "Internal server error"}, status=500)