from functools import wraps
from django.conf import settings
from .client import mixpanel_client
import logging

logger = logging.getLogger(__name__)

def track_api_event(event_name: str, properties_func=None):
    """
    Decorator to track API events in Mixpanel
    
    Args:
        event_name: Name of the event to track
        properties_func: Optional function to generate properties from request/response
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Execute the original function
            response = func(request, *args, **kwargs)
            
            # Track the event
            try:
                # Get user ID from request
                user_id = None
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user_id = getattr(request.user, 'clerk_user_id', str(request.user.id))
                elif hasattr(request, 'clerk_user_id'):
                    user_id = request.clerk_user_id
                
                if user_id:
                    # Generate properties if function provided
                    properties = {}
                    if properties_func:
                        try:
                            properties = properties_func(request, response, *args, **kwargs)
                        except Exception as e:
                            logger.error(f"Error generating properties: {e}")
                    
                    # Add default API properties
                    properties.update({
                        'endpoint': request.path,
                        'method': request.method,
                        'status_code': getattr(response, 'status_code', None),
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': _get_client_ip(request),
                    })
                    
                    mixpanel_client.track_api_event(user_id, event_name, properties)
                    
            except Exception as e:
                logger.error(f"Error tracking API event {event_name}: {e}")
            
            return response
        return wrapper
    return decorator

def _get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip