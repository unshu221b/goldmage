import logging
from helpers.myclerk.utils import (
    get_clerk_user_id_from_request,
    update_or_create_clerk_user
)

logger = logging.getLogger('goldmage')

def django_user_session_via_clerk(request):
    clerk_user_id = get_clerk_user_id_from_request(request)
    if not clerk_user_id:
        logger.debug("No Clerk user ID found in request")
        return None
    logger.info(f"Found Clerk user ID: {clerk_user_id}")
    django_user, created = update_or_create_clerk_user(clerk_user_id)
    if created:
        logger.info(f"Created new Django user for Clerk ID: {clerk_user_id}")
    elif django_user:
        logger.info(f"Found existing Django user for Clerk ID: {clerk_user_id}")
    else:
        logger.warning(f"Failed to create/find Django user for Clerk ID: {clerk_user_id}")
    return django_user


class ClerkAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = django_user_session_via_clerk(request)
        if user:
            request.user = user
            logger.debug(f"Set user in request: {user.clerk_user_id}")
        return self.get_response(request)