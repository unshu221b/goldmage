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
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def get_pattern_data(self):
        """Analyze login patterns for this attempt"""
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Calculate daily attempts first
        day_attempts_ip = LoginAttempt.objects.filter(
            ip_address=self.ip_address,
            timestamp__gte=day_ago
        ).count()
        
        # Calculate success rate
        day_successful_attempts = LoginAttempt.objects.filter(
            ip_address=self.ip_address,
            timestamp__gte=day_ago,
            was_successful=True
        ).count()
        
        success_rate = day_successful_attempts / max(day_attempts_ip, 1)
        
        return {
            # Hourly patterns
            'hour_attempts_ip': LoginAttempt.objects.filter(
                ip_address=self.ip_address,
                timestamp__gte=hour_ago
            ).count(),
            
            'hour_attempts_email': LoginAttempt.objects.filter(
                email=self.email,
                timestamp__gte=hour_ago
            ).count(),
            
            'hour_unique_ips_for_email': LoginAttempt.objects.filter(
                email=self.email,
                timestamp__gte=hour_ago
            ).values('ip_address').distinct().count(),
            
            # Daily patterns
            'day_attempts_ip': day_attempts_ip,
            'day_successful_attempts': day_successful_attempts,
            'success_rate_ip': success_rate,
            
            'day_unique_emails_from_ip': LoginAttempt.objects.filter(
                ip_address=self.ip_address,
                timestamp__gte=day_ago
            ).values('email').distinct().count(),
            
            # Time patterns
            'odd_hours': self.timestamp.hour in range(1, 5),  # 1 AM to 5 AM
            
            # Geographic anomalies (if available)
            'different_country': self.country and LoginAttempt.objects.filter(
                email=self.email,
                was_successful=True
            ).exclude(country=self.country).exists(),
        }
    
    @property
    def is_suspicious(self):
        """
        Determine if this login attempt is suspicious based on multiple factors
        Returns: (bool, list of reasons)
        """
        patterns = self.get_pattern_data()
        reasons = []
        
        # Hourly thresholds
        if patterns['hour_attempts_ip'] > 10:
            reasons.append(f"Too many attempts from IP ({patterns['hour_attempts_ip']} in 1h)")
            
        if patterns['hour_unique_ips_for_email'] > 3:
            reasons.append(f"Email tried from multiple IPs ({patterns['hour_unique_ips_for_email']} in 1h)")
            
        # Daily thresholds
        if patterns['day_unique_emails_from_ip'] > 10:
            reasons.append(f"IP trying multiple emails ({patterns['day_unique_emails_from_ip']} in 24h)")
            
        # Success rate
        if patterns['success_rate_ip'] < 0.1 and patterns['day_attempts_ip'] > 5:
            reasons.append("Very low success rate from this IP")
            
        # Time patterns
        if patterns['odd_hours']:
            reasons.append("Attempt during unusual hours")
            
        # Geographic anomalies
        if patterns['different_country']:
            reasons.append("Attempt from different country than successful logins")
        
        return bool(reasons), reasons

    def __str__(self):
        return f"{self.email} from {self.ip_address} at {self.timestamp}"