from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class ClerkAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            token = auth_header.split(' ')[1]
            payload = jwt.decode(
                token,
                settings.CLERK_PUBLIC_KEY,
                algorithms=['RS256'],
                audience=settings.CLERK_AUDIENCE
            )
            
            clerk_user_id = payload['sub']
            user, created = User.objects.get_or_create(
                clerk_user_id=clerk_user_id, 
                defaults={
                    'email': payload.get('email'),
                    'username': payload.get('email')
                }
            )
            
            return (user, None)
        except Exception as e:
            raise AuthenticationFailed(str(e))