# from django.conf import settings
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from datetime import timedelta
from cloudinary.models import CloudinaryField
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, clerk_user_id, **extra_fields):
        if not clerk_user_id:
            raise ValueError('Clerk ID is required')
        
        user = self.model(clerk_user_id=clerk_user_id, **extra_fields)
        user.is_active = True
        user.save()
        return user

class CustomUser(AbstractBaseUser):
    # user = models.OneToOneField(User, on_delete=models.CASCADE)
    clerk_user_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_provider = models.BooleanField(default=False)
    # django login related
    is_active = models.BooleanField(default=True)
    # django admin related
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "clerk_user_id"
    REQUIRED_FIELDS= []

    objects = CustomUserManager()

    MEMBERSHIP_CHOICES = [
        ('FREE', 'Free'),
        ('PREMIUM', 'Premium'),
    ]
    membership = models.CharField(
        max_length=10,
        choices=MEMBERSHIP_CHOICES,
        default='FREE'
    )
    # Credit system fields
    credits = models.IntegerField(default=50)  # Daily EP points
    last_depleted_time = models.DateTimeField(null=True, blank=True)

    total_usage_14d = models.IntegerField(default=0)  # Track 14-day usage
    last_usage_timestamp = models.DateTimeField(null=True, blank=True)
    is_thread_depth_locked = models.BooleanField(default=False)
  
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True
    
    def add_credits(self, amount):
        """Add credits to user's account"""
        self.credits += amount
        self.save()

    def use_credit(self, event_type="Message", cost=1, kind="Monthly Credits", model_name=None):
        """Use one credit (EP), returns True if successful, False if no credits left"""
        # Check and refill credits if it's time
        self.check_and_refill_credits()
        if self.credits > 0:
            self.credits -= 1
            if self.credits == 0:
                self.last_depleted_time = timezone.now()  # Start vesting timer
            self.update_14d_usage()
            self.check_thread_depth_lock()
            self.save()
            CreditUsageHistory.objects.create(
                user=self,
                event_type=event_type,
                cost=cost,
                kind=kind,
                model=model_name
            )
            return True
        return False
    
    def get_daily_refill_time(self):
        """no daily refill, change to vesting schedule"""
        if self.credits > 0 or not self.last_depleted_time:
            return None  # No refill scheduled, user still has credits
        
        if self.is_thread_depth_locked:
            return self.last_depleted_time + timedelta(days=7)
        else:
            return self.last_depleted_time + timedelta(hours=8)

    def check_and_refill_credits(self):
        now = timezone.now()
        # Only refill if user has zero credits and a depletion time is set
        if self.credits == 0 and self.last_depleted_time:
            if self.is_thread_depth_locked:
                next_refill = self.last_depleted_time + timedelta(days=7)

            else:
                next_refill = self.last_depleted_time + timedelta(hours=12)

            if now >= next_refill:
                # Refill credits
                self.credits = 50
                self.last_depleted_time = None  # Reset depletion time
                if self.is_thread_depth_locked:
                    self.is_thread_depth_locked = False
                    self.total_usage_14d = 0
                self.save()
                return True
        return False

    def update_14d_usage(self):
        """Update 14-day usage tracking (only for free users)"""
        if self.membership == 'PREMIUM':
            return  # Premium users don't track usage

        now = timezone.now()
        if self.last_usage_timestamp:
            # If last usage was more than 14 days ago, reset counter
            if now - self.last_usage_timestamp > timedelta(days=14):
                self.total_usage_14d = 0
            # If last usage was today, increment counter
            elif self.last_usage_timestamp.date() == now.date():
                self.total_usage_14d += 1
        else:
            self.total_usage_14d = 1
        
        self.last_usage_timestamp = now
        self.save()

    def check_thread_depth_lock(self):
        """Check if user should be thread depth locked (only for free users)"""
        if self.membership == 'PREMIUM':
            self.is_thread_depth_locked = False
            self.save()
            return False

        if self.total_usage_14d >= 650:
            self.is_thread_depth_locked = True
            # Reset the 14-day usage counter when thread locked
            self.total_usage_14d = 0
            self.save()
            return True
        return False

    def get_remaining_credits(self):
        """Get remaining credits"""
        self.check_and_refill_credits()  # Check for refill before returning
        return self.credits
    
    def initialize_free_credits(self):
        """Initialize free credits for new users"""
        if self.credits == 0:  # Only initialize if no credits exist
            self.credits = 50
            self.save()
            return True
        return False
    
    def save(self, *args, **kwargs):
        # Initialize credits if they don't exist
        if not hasattr(self, 'credits'):
            self.credits = 50
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
class Conversation(models.Model):
    id = models.BigAutoField(primary_key=True)  # Keep the existing ID
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Add UUID
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=50)  # "user", "assistant", "system"
    input_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('image_upload', 'Image Upload'),
            ('social_link_upload', 'Social Link Upload'),
        ]
    )
    text_content = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    builder_data = models.JSONField(blank=True, null=True)
    analysis_data = models.JSONField(blank=True, null=True)  # For analysis data
    type = models.CharField(
        max_length=20,
        choices=[
            ('builder', 'Builder'),
            ('creator', 'Creator'),
            ('editor', 'Editor'),
            ('analysis', 'Analysis'),
            ('system', 'System'),
            ('loading', 'Loading'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']  # Always get messages in order

class FavoriteConversation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='favorite_conversations')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'conversation')  # Prevent duplicate favorites
        ordering = ['-created_at']  # Most recent favorites first

    def __str__(self):
        return f"{self.user.username}'s favorite: {self.conversation.title}"

class CreditUsageHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='credit_usages')
    event_type = models.CharField(max_length=50)  # e.g., "Message"
    cost = models.DecimalField(max_digits=6, decimal_places=2)  # e.g., 0.23
    date = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=50, default="Monthly Credits")  # or "Pay-as-you-go", etc.
    model = models.CharField(max_length=50, blank=True, null=True)  # e.g., "v0-1.5-md"

    class Meta:
        ordering = ['-date']

class Vault(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Provider(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='providers')
    vault = models.ForeignKey(Vault, on_delete=models.CASCADE, related_name='providers')
    name = models.CharField(max_length=150)
    bio = models.TextField(blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    contact_link = models.URLField(blank=True, null=True)
    language_support = models.JSONField(default=list, blank=True)
    specialties = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    qualifications = models.JSONField(default=dict, blank=True)  # experience, degree, etc.
    social_profiles = models.JSONField(default=list, blank=True)
    availability = models.JSONField(default=dict, blank=True)    # days, hours, duration, etc.
    agreed_to_terms = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)  # Add this if you want to approve listings
    icon = CloudinaryField('icon', blank=True, null=True)

    def __str__(self):
        return self.name

class ProviderTag(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='tags')
    tag = models.CharField(max_length=50)

    def __str__(self):
        return self.tag

class ProviderReview(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='reviews')
    user_id = models.IntegerField()  # Or ForeignKey to your User model
    rating = models.PositiveSmallIntegerField()
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider.name} - {self.rating}"

# Embeddings model is optional and depends on your vector DB setup
class Embedding(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='embeddings')
    vector = models.JSONField()  # Or use a custom field for your vector DB

    def __str__(self):
        return f"Embedding for {self.provider.name}"

class ServiceOffering(models.Model):
    id = models.BigAutoField(primary_key=True)  # Keep the existing ID
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='offerings')
    service_title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    offerings = models.JSONField(default=list, blank=True)  # List of {name, price}
    pricing = models.JSONField(default=dict, blank=True)    # {basePrice, serviceFee}
    travel_option = models.CharField(max_length=50, blank=True, null=True)
    venue_address = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    thumbnail = CloudinaryField('thumbnail', blank=True, null=True)

    def __str__(self):
        return f"{self.service_title} ({self.provider.name})"

