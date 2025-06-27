import mixpanel
from django.conf import settings
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MixpanelClient:
    """
    Server-side Mixpanel client for Django API tracking
    """
    
    def __init__(self):
        self.client = None
        self.enabled = getattr(settings, 'MIXPANEL_ENABLED', True)
        
        if self.enabled and hasattr(settings, 'MIXPANEL_TOKEN') and settings.MIXPANEL_TOKEN:
            try:
                self.client = mixpanel.Mixpanel(settings.MIXPANEL_TOKEN)
                logger.info("Mixpanel client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Mixpanel client: {e}")
                self.client = None
        else:
            logger.warning("Mixpanel is disabled or token not configured")
    
    def track_api_event(self, user_id: str, event_name: str, properties: Optional[Dict[str, Any]] = None):
        """
        Track an API event for a specific user
        
        Args:
            user_id: Unique identifier for the user (clerk_user_id)
            event_name: Name of the event to track
            properties: Additional properties for the event
        """
        if not self.client or not self.enabled:
            return
            
        try:
            event_properties = properties or {}
            event_properties.update({
                'server_side': True,
                'timestamp': datetime.utcnow().isoformat(),
                'platform': 'api',
            })
            
            self.client.track(user_id, event_name, event_properties)
            logger.debug(f"Tracked API event '{event_name}' for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to track API event '{event_name}': {e}")
    
    def track_user_signup(self, user_id: str, properties: Optional[Dict[str, Any]] = None):
        """Track user signup event"""
        signup_properties = properties or {}
        signup_properties.update({
            'signup_method': 'clerk',
            'platform': 'api',
        })
        self.track_api_event(user_id, 'User Signup', signup_properties)
    
    def track_user_login(self, user_id: str, properties: Optional[Dict[str, Any]] = None):
        """Track user login event"""
        login_properties = properties or {}
        login_properties.update({
            'login_method': 'clerk',
            'platform': 'api',
        })
        self.track_api_event(user_id, 'User Login', login_properties)
    
    def track_checkout_session_created(self, user_id: str, period: str, properties: Optional[Dict[str, Any]] = None):
        """Track checkout session creation"""
        checkout_properties = properties or {}
        checkout_properties.update({
            'subscription_period': period,
            'platform': 'api',
        })
        self.track_api_event(user_id, 'Checkout Session Created', checkout_properties)
    
    def track_analysis_requested(self, user_id: str, analysis_type: str, properties: Optional[Dict[str, Any]] = None):
        """Track analysis requests"""
        analysis_properties = properties or {}
        analysis_properties.update({
            'analysis_type': analysis_type,
            'platform': 'api',
        })
        self.track_api_event(user_id, 'Analysis Requested', analysis_properties)
    
    def track_message_sent(self, user_id: str, message_type: str, properties: Optional[Dict[str, Any]] = None):
        """Track message sending"""
        message_properties = properties or {}
        message_properties.update({
            'message_type': message_type,
            'platform': 'api',
        })
        self.track_api_event(user_id, 'Message Sent', message_properties)
    
    def track_credit_used(self, user_id: str, credit_amount: int, properties: Optional[Dict[str, Any]] = None):
        """Track credit usage"""
        credit_properties = properties or {}
        credit_properties.update({
            'credits_used': credit_amount,
            'platform': 'api',
        })
        self.track_api_event(user_id, 'Credit Used', credit_properties)
    
    def set_user_properties(self, user_id: str, properties: Dict[str, Any]):
        """Set properties for a specific user"""
        if not self.client or not self.enabled:
            return
            
        try:
            self.client.people_set(user_id, properties)
            logger.debug(f"Set properties for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to set properties for user {user_id}: {e}")

# Global instance
mixpanel_client = MixpanelClient()