from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser

class CustomUserManager(BaseUserManager):
    def create_user(self, clerk_user_id, **extra_fields):
        if not clerk_user_id:
            raise ValueError('Clerk ID is required')
        
        user = self.model(clerk_user_id=clerk_user_id, **extra_fields)
        user.is_active = True
        user.save()
        return user
    
class CustomUser(AbstractBaseUser):
    clerk_user_id = models.CharField(max_length=255, unique=True, db_index=True)

    username = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(max_length=500, null=True, blank=True)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)

    # django login related
    is_active = models.BooleanField(default=True)
    # django admin related
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "clerk_user_id"
    REQUIRED_FIELDS= []

    objects = CustomUserManager()
    # Account type for subscription
    ACCOUNT_TYPES = (
        ('FREE', 'Free'),
        ('PRO', 'Pro'),
    )
    account_type = models.CharField(
        max_length=10, 
        choices=ACCOUNT_TYPES, 
        default='FREE',
        help_text='Type of account subscription'
    )

    @property
    def is_premium(self):
        """Check if user has premium access"""
        return self.account_type == 'PRO'
    
    def has_active_subscription(self):
        """Check subscription status using clerk_user_id as Stripe customer ID"""
        if not self.clerk_user_id:
            return False
        return self.account_type == 'PRO'