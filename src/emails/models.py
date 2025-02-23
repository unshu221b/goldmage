import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.safestring import mark_safe

class EmailUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Email(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Add Stripe customer ID field
    customer_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text='Stripe customer ID'
    )

    # New account type field
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

    # Add related_name to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='email_set',  # Changed from user_set
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='email_set',  # Changed from user_set
        help_text='Specific permissions for this user.'
    )

    objects = EmailUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_premium(self):
        """Check if user has premium access"""
        return self.account_type == 'PRO'
    
    def has_active_subscription(self):
        """More detailed check for subscription status"""
        if not self.customer_id:
            return False
        return self.account_type == 'PRO'

# class Purchase(models.Model):
#     email = models.ForeignKey(Email, on_delete=models.SET_NULL, null=True)
#     course =  models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)


class EmailVerificationEvent(models.Model):
    EVENT_TYPES = (
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    )
    
    parent = models.ForeignKey(Email, on_delete=models.SET_NULL, null=True)
    email = models.EmailField()
    #  token
    token = models.UUIDField(default=uuid.uuid1)
    event_type = models.CharField(
        max_length=50, 
        choices=EVENT_TYPES,
        default='registration'  # Set default for existing records
    )
    metadata = models.JSONField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(
        auto_now=False,
        auto_now_add=False,
        blank=True,
        null=True
    )
    expired = models.BooleanField(default=False)
    expired_at = models.DateTimeField(
        auto_now=False,
        auto_now_add=False,
        blank=True,
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)


    def get_link(self):
        return f"{settings.BASE_URL}/verify/{self.token}/"

class LoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    was_successful = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
    
    def get_pattern_data(self):
        """Analyze basic login patterns for rate limiting"""
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        
        return {
            # Hourly attempts for rate limiting
            'hour_attempts_ip': LoginAttempt.objects.filter(
                ip_address=self.ip_address,
                timestamp__gte=hour_ago
            ).count(),
            
            'hour_attempts_email': LoginAttempt.objects.filter(
                email=self.email,
                timestamp__gte=hour_ago
            ).count(),
        }
    
    @property
    def is_suspicious(self):
        """
        Simple rate limit check
        Returns: (bool, list of reasons)
        """
        patterns = self.get_pattern_data()
        reasons = []
        
        # Only check for basic rate limiting
        if patterns['hour_attempts_ip'] > 20:  # More lenient IP threshold
            reasons.append(f"Rate limit exceeded for IP")
            
        if patterns['hour_attempts_email'] > 10:  # Stricter email threshold
            reasons.append(f"Rate limit exceeded for email")
            
        return bool(reasons), reasons

    def __str__(self):
        return f"{self.email} from {self.ip_address} at {self.timestamp}"