import json
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions

from django.conf import settings
from django.contrib.auth import get_user_model

import warnings
import logging
import jwt

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
        
        # Get the token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            logger.warning("No Bearer token found in Authorization header")
            return None
            
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        logger.info(f"Received token: {token[:20]}...")
        
        # Verify the token
        request_state = sdk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=CLERK_AUTH_PARTIES
            )
        )
        
        if not request_state.is_signed_in:
            logger.warning("User is not signed in according to Clerk")
            return None
            
        # Extract user ID from the token
        # The token is a JWT and we can see from the logs that it contains 'sub' claim
        # which is the user ID
        try:
            # The token is already verified by authenticate_request
            # We can safely decode it to get the user ID
            decoded = jwt.decode(token, options={"verify_signature": False})
            clerk_user_id = decoded.get('sub')
            
            if clerk_user_id:
                logger.debug(f"Successfully extracted Clerk user ID: {clerk_user_id}")
                return clerk_user_id
            else:
                logger.warning("No 'sub' claim found in token")
                return None
                
        except Exception as e:
            logger.error(f"Error decoding JWT token: {str(e)}", exc_info=True)
            return None
            
    except Exception as e:
        logger.error(f"Error authenticating request with Clerk: {str(e)}", exc_info=True)
        return None


def update_or_create_clerk_user(clerk_user_id):
    if not clerk_user_id:
        logger.warning("No clerk_user_id provided")
        return None, None
        
    sdk = Clerk(bearer_auth=CLERK_SECRET_KEY)
    try:
        # Get user data and convert to dict
        clerk_user = sdk.users.get(user_id=clerk_user_id)
        if not clerk_user:
            logger.warning(f"No Clerk user found for ID: {clerk_user_id}")
            return None, None
            
        # Convert to dict and handle any serialization issues
        try:
            user_data = json.loads(clerk_user.model_dump_json())
        except Exception as e:
            logger.error(f"Error serializing Clerk user data: {str(e)}")
            # Fallback to manual extraction
            user_data = {
                'username': getattr(clerk_user, 'username', None),
                'first_name': getattr(clerk_user, 'first_name', None),
                'last_name': getattr(clerk_user, 'last_name', None),
                'email_addresses': getattr(clerk_user, 'email_addresses', []),
                'primary_email_address_id': getattr(clerk_user, 'primary_email_address_id', None)
            }
        
        logger.info(f"Clerk user data: {user_data}")
        
        # Get primary email
        primary_email = None
        if user_data.get('email_addresses'):
            primary_email_id = user_data.get('primary_email_address_id')
            for email in user_data['email_addresses']:
                if isinstance(email, dict) and email.get('id') == primary_email_id:
                    primary_email = email.get('email_address')
                    break
                elif hasattr(email, 'id') and email.id == primary_email_id:
                    primary_email = email.email_address
                    break
        
        # Prepare user data with defaults for missing fields
        django_user_data = {
            "username": user_data.get('username') or f"user_{clerk_user_id[-8:]}",
            "first_name": user_data.get('first_name') or "",
            "last_name": user_data.get('last_name') or "",
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
    