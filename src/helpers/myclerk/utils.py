import json
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions

from django.conf import settings
from django.contrib.auth import get_user_model

import warnings
import logging

# Suppress all warnings from a specific package
warnings.filterwarnings("ignore", module="clerk_backend_api")
warnings.filterwarnings("ignore", module="pydantic")

CLERK_SECRET_KEY = settings.CLERK_SECRET_KEY
CLERK_AUTH_PARTIES = settings.CLERK_AUTH_PARTIES

User = get_user_model()
logger = logging.getLogger('goldmage')


def get_clerk_user_id_from_request(request):
    sdk = Clerk(bearer_auth=CLERK_SECRET_KEY)
    try:
        logger.info("Attempting to authenticate request with Clerk")
        logger.info(f"Using CLERK_AUTH_PARTIES: {CLERK_AUTH_PARTIES}")
        
        # Log the token for debugging (remove in production)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            logger.info(f"Received token: {token[:20]}...")
        
        request_state = sdk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=CLERK_AUTH_PARTIES
            )
        )
        
        if not request_state.is_signed_in:
            logger.warning("User is not signed in according to Clerk")
            logger.warning(f"Request state: {request_state}")
            return None
            
        # Get the session ID from the request state
        session_id = request_state.session_id
        if not session_id:
            logger.warning("No session ID found in request state")
            return None
            
        # Get the user ID from the session
        session = sdk.sessions.get(session_id)
        if not session:
            logger.warning(f"No session found for ID: {session_id}")
            return None
            
        clerk_user_id = session.user_id
        if clerk_user_id:
            logger.debug(f"Successfully extracted Clerk user ID: {clerk_user_id}")
        else:
            logger.warning("No user ID found in session")
        return clerk_user_id
    except Exception as e:
        logger.error(f"Error authenticating request with Clerk: {str(e)}", exc_info=True)
        return None


def update_or_create_clerk_user(clerk_user_id):
    if not clerk_user_id:
        logger.warning("No clerk_user_id provided")
        return None, None
        
    sdk = Clerk(bearer_auth=CLERK_SECRET_KEY)
    try:
        clerk_user = sdk.users.get(user_id=clerk_user_id)
        if not clerk_user:
            logger.warning(f"No Clerk user found for ID: {clerk_user_id}")
            return None, None
            
        # Log the full Clerk user data for debugging
        logger.info(f"Clerk user data: {clerk_user.model_dump_json()}")
        
        # Get primary email
        primary_email_address_id = clerk_user.primary_email_address_id
        primary_email = next(
            (email.email_address for email in clerk_user.email_addresses if email.id == primary_email_address_id),
            None
        )
        
        # Prepare user data with defaults for missing fields
        django_user_data = {
            "username": clerk_user.username or "",
            "first_name": clerk_user.first_name or "",
            "last_name": clerk_user.last_name or "",
            "email": primary_email or "",
        }
        
        logger.info(f"Attempting to create/update user with data: {django_user_data}")
        
        try:
            user_obj, created = User.objects.update_or_create(
                clerk_user_id=clerk_user_id,
                defaults=django_user_data
            )
            
            if created:
                logger.info(f"Created new user with ID: {user_obj.id}")
            else:
                logger.info(f"Updated existing user with ID: {user_obj.id}")
                
            return user_obj, created
            
        except Exception as e:
            logger.error(f"Database error while creating/updating user: {str(e)}", exc_info=True)
            return None, None
            
    except Exception as e:
        logger.error(f"Error fetching Clerk user data: {str(e)}", exc_info=True)
        return None, None
    