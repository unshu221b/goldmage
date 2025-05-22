# from django.conf import settings
from django.db import models
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
    
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
class Conversation(models.Model):
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
