# from django.conf import settings
from django.db import models
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from datetime import timedelta
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

    username = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # django login related
    is_active = models.BooleanField(default=True)
    # django admin related
    is_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "clerk_user_id"
    REQUIRED_FIELDS= []

    objects = CustomUserManager()

    MEMBERSHIP_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]
    membership = models.CharField(
        max_length=10,
        choices=MEMBERSHIP_CHOICES,
        default='free'
    )
    # Credit system fields
    credits = models.IntegerField(default=10)  # Daily EP points
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

    def use_credit(self):
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
                next_refill = self.last_depleted_time + timedelta(hours=8)

            if now >= next_refill:
                # Refill credits
                self.credits = 200 if self.membership == 'premium' else 10
                self.last_depleted_time = None  # Reset depletion time
                if self.is_thread_depth_locked:
                    self.is_thread_depth_locked = False
                    self.total_usage_14d = 0
                self.save()
                return True
        return False

    def update_14d_usage(self):
        """Update 14-day usage tracking (only for free users)"""
        if self.membership == 'premium':
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
        if self.membership == 'premium':
            self.is_thread_depth_locked = False
            self.save()
            return False

        if self.total_usage_14d >= 140:
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
            self.credits = 10
            self.save()
            return True
        return False
    
    def save(self, *args, **kwargs):
        # Initialize credits if they don't exist
        if not hasattr(self, 'credits'):
            self.credits = 10
        super().save(*args, **kwargs)

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=50)  # "user" or "assistant"
    input_type = models.CharField(max_length=10, choices=[('text', 'Text'), ('image', 'Image')])
    text_content = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ConversationAnalysis(models.Model):
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='analysis')
    reaction = models.TextField()  # The main analysis response/passage
    suggestions = models.JSONField()  # Store the 4 suggestions as a JSON array
    personality_metrics = models.JSONField()  # Store personality metrics
    emotion_metrics = models.JSONField()  # Store emotion metrics
    dominant_emotion = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MessageAnalysis(models.Model):
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='analysis')
    dominant_emotion = models.CharField(max_length=50)
    emotion_scores = models.JSONField()  # e.g., {"happiness": 15, "sadness": 35, ...}
    summary = models.TextField(blank=True, null=True)
