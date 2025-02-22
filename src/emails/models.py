import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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
    parent = models.ForeignKey(Email, on_delete=models.SET_NULL, null=True)
    email = models.EmailField() 
    #  token
    token = models.UUIDField(default=uuid.uuid1)
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