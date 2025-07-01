import logging
from helpers.myclerk.utils import (
    get_clerk_user_id_from_request,
    update_or_create_clerk_user
)
from django.conf import settings

logger = logging.getLogger('goldmage')

def django_user_session_via_clerk(request):
    # Check if Clerk is properly configured
    if not settings.CLERK_SECRET_KEY:
        logger.error("CLERK_SECRET_KEY is not set in settings")
        return None
        
    # Log all relevant headers
    logger.info("Request headers:")
    for header, value in request.headers.items():
        if header.lower() in ['authorization', 'x-clerk-token', 'cookie', 'origin']:
            logger.info(f"{header}: {value}")
    
    clerk_user_id = get_clerk_user_id_from_request(request)
    if not clerk_user_id:
        logger.debug("No Clerk user ID found in request")
        return None
    logger.info(f"Found Clerk user ID: {clerk_user_id}")
    django_user, created = update_or_create_clerk_user(clerk_user_id, request)
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
        # List of paths that don't need authentication
        self.exempt_paths = [
            '/webhook/',
            '/webhook/clerk/',
            '/health/',
            '/__reload__/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Skip authentication for exempt paths
        if any(request.path.startswith(path) for path in self.exempt_paths):
            return self.get_response(request)

        try:
            logger.info(f"Processing request to: {request.path}")
            logger.info(f"Request method: {request.method}")
            logger.info(f"Request origin: {request.headers.get('origin', 'No origin')}")
            logger.info(f"Request host: {request.get_host()}")
            logger.info(f"Request scheme: {request.scheme}")
            
            user = django_user_session_via_clerk(request)
            if user:
                request.user = user
                logger.debug(f"Set user in request: {user.clerk_user_id}")
            else:
                logger.warning(f"No user found for request to: {request.path}")
                # Don't set request.user to None, let Django handle it
        except Exception as e:
            logger.error(f"Error in ClerkAuthMiddleware: {str(e)}", exc_info=True)
            # Don't block the request, let it continue without authentication
            
        return self.get_response(request)