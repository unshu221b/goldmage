from django.contrib.auth.models import AnonymousUser
import logging

from helpers.myclerk.utils import (
    get_clerk_user_id_from_request,
    update_or_create_clerk_user
)

logger = logging.getLogger(__name__)

def django_user_session_via_clerk(request):
    clerk_user_id = get_clerk_user_id_from_request(request)
    if not clerk_user_id:
        return None
    django_user, _ = update_or_create_clerk_user(clerk_user_id)
    return django_user


class ClerkAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = django_user_session_via_clerk(request)
        logger.info(f"Middleware - User authenticated: {user is not None}")
        if user:
            request.user = user
        else:
            request.user = AnonymousUser()
        return self.get_response(request)