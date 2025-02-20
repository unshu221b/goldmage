import uuid
import helpers
from django.db import models
from django.utils.text import slugify
from cloudinary.models import CloudinaryField
from django.contrib.auth.models import User
from django.conf import settings

helpers.cloudinary_init()

class AccessRequirement(models.TextChoices):
    ANYONE = "any", "Anyone"
    EMAIL_REQUIRED = "email", "Email required"

class PublishStatus(models.TextChoices):
    PUBLISHED = "publish", "Published"
    COMING_SOON = "soon", "Coming Soon"
    DRAFT = "draft", "Draft"


def handle_upload(instance, filename):
    return f"{filename}"

# from courses.models import Course
# Course.objects.all() -> list out all courses
# Course.objects.first() -> first row of all courses

def generate_public_id(instance, *args, **kwargs):
    title = instance.title
    unique_id = str(uuid.uuid4()).replace("-", "")
    if not title:
        return unique_id
    slug = slugify(title)
    unique_id_short = unique_id[:5]
    return f"{slug}-{unique_id_short}"


def get_public_id_prefix(instance, *args, **kwargs):
    if hasattr(instance, 'path'):
        path = instance.path
        if path.startswith("/"):
            path = path[1:]
        if path.endswith('/'):
            path = path[:-1]
        return path
    public_id = instance.public_id
    model_class = instance.__class__
    model_name = model_class.__name__
    model_name_slug = slugify(model_name)
    if not public_id:
        return f"{model_name_slug}"
    return f"{model_name_slug}/{public_id}"

def get_display_name(instance, *args, **kwargs):
    if hasattr(instance, 'get_display_name'):
        return instance.get_display_name()
    elif hasattr(instance, 'title'):
        return instance.title
    model_class = instance.__class__
    model_name = model_class.__name__
    return f"{model_name} Upload"

# get_thumbnail_display_name = lambda instance: get_display_name(instance, is_thumbnail=True)

class Course(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    # uuid = models.UUIDField(default=uuid.uuid1, unique=True)
    public_id = models.CharField(max_length=130, blank=True, null=True, db_index=True)
    # image = models.ImageField(upload_to=handle_upload, blank=True, null=True)
    image = CloudinaryField(
        "image", 
        null=True, 
        public_id_prefix=get_public_id_prefix,
        display_name=get_display_name,
        tags=["course", "thumbnail"]
    )
    access = models.CharField(
        max_length=5, 
        choices=AccessRequirement.choices,
        default=AccessRequirement.EMAIL_REQUIRED
    )
    status = models.CharField(
        max_length=10, 
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT
        )
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # before save
        if self.public_id == "" or self.public_id is None:
            self.public_id = generate_public_id(self)
        super().save(*args, **kwargs)
        # after save

    def get_absolute_url(self):
        return self.path
    
    @property
    def path(self):
        return f"/courses/{self.public_id}"

    def get_display_name(self):
        return f"{self.title} - Course"

    def get_thumbnail(self):
        if not self.image:
            return None
        return helpers.get_cloudinary_image_object(
            self, 
            field_name='image',
            as_html=False,
            width=382
        )

    def get_display_image(self):
        if not self.image:
            return None
        return helpers.get_cloudinary_image_object(
            self, 
            field_name='image',
            as_html=False,
            width=750
        )

    @property
    def is_published(self):
        return self.status == PublishStatus.PUBLISHED
    

"""
- Lessons
    - Title
    - Description
    - Video
    - Status: Published, Coming Soon, Draft
"""

# Lesson.objects.all() # lesson queryset -> all rows
# Lesson.objects.first()
# course_obj = Course.objects.first()
# course_qs = Course.objects.filter(id=course_obj.id)
# Lesson.objects.filter(course__id=course_obj.id)
# course_obj.lesson_set.all()
# lesson_obj = Lesson.objects.first()
# ne_course_obj = lesson_obj.course
# ne_course_lessons = ne_course_obj.lesson_set.all()
# lesson_obj.course_id
# course_obj.lesson_set.all().order_by("-title")

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    # course_id 
    public_id = models.CharField(max_length=130, blank=True, null=True, db_index=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    thumbnail = CloudinaryField("image", 
                public_id_prefix=get_public_id_prefix,
                display_name=get_display_name,
                tags = ['thumbnail', 'lesson'],
                blank=True, null=True)
    video = CloudinaryField("video", 
            public_id_prefix=get_public_id_prefix,
            display_name=get_display_name,                
            blank=True, 
            null=True, 
            type='private',
            tags = ['video', 'lesson'],
            resource_type='video')
    order = models.IntegerField(default=0)
    can_preview = models.BooleanField(default=False, help_text="If user does not have access to course, can they see this?")
    status = models.CharField(
        max_length=10, 
        choices=PublishStatus.choices,
        default=PublishStatus.PUBLISHED
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    duration_seconds = models.IntegerField(null=True, blank=True)  # Store duration in seconds
    
    is_featured = models.BooleanField(default=False, help_text="Display this lesson in featured section")
    featured_order = models.IntegerField(default=0, help_text="Order in featured section")

    class Meta:
        ordering = ['order', 'featured_order', '-updated']

    def save(self, *args, **kwargs):
        # before save
        if self.public_id == "" or self.public_id is None:
            self.public_id = generate_public_id(self)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return self.path

    @property
    def path(self):
        course_path = self.course.path
        if course_path.endswith("/"):
            course_path = course_path[:-1]
        return f"{course_path}/lessons/{self.public_id}"

    @property
    def requires_email(self):
        return self.course.access == AccessRequirement.EMAIL_REQUIRED

    def get_display_name(self):
        return f"{self.title} - {self.course.get_display_name()}"

    @property
    def is_coming_soon(self):
        return self.status == PublishStatus.COMING_SOON
    
    @property
    def has_video(self):
        return self.video is not None
    
    def get_thumbnail(self):
        width = 382
        if self.thumbnail:
            return helpers.get_cloudinary_image_object(
                self, 
                field_name='thumbnail',
                format='jpg',
                as_html=False,
                width=width
            )
        elif self.video:
            return helpers.get_cloudinary_image_object(
            self, 
            field_name='video',
            format='jpg',
            as_html=False,
            width=width
        )
        return 

    def get_progress(self, user):
        """Get the watch progress for a specific user"""
        try:
            progress = WatchProgress.objects.get(user=user, lesson=self)
            return round((progress.current_time / progress.total_duration) * 100)
        except WatchProgress.DoesNotExist:
            return 0

    @property
    def duration(self):
        if not self.duration_seconds:
            return None
            
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @classmethod
    def get_featured(cls):
        return cls.objects.filter(
            is_featured=True,
            status=PublishStatus.PUBLISHED,
            course__status=PublishStatus.PUBLISHED  # Ensure parent course is also published
        ).select_related('course').order_by('featured_order', '-updated')

    def get_related_lessons(self, limit=5):
        """Get related lessons from the same course"""
        return Lesson.objects.filter(
            course=self.course,
            status=PublishStatus.PUBLISHED
        ).exclude(id=self.id).order_by('order')[:limit]

class WatchProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    current_time = models.FloatField(default=0)  # in seconds
    total_duration = models.FloatField(default=0)  # in seconds
    last_watched = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'lesson']
        indexes = [
            models.Index(fields=['-last_watched']),
        ]

    @property
    def progress_percentage(self):
        """Calculate the percentage of video watched"""
        if self.total_duration > 0:
            return min(round((self.current_time / self.total_duration) * 100), 100)
        return 0

    def update_progress(self, current_time):
        self.current_time = current_time
        if self.total_duration > 0 and (current_time / self.total_duration) > 0.9:
            self.completed = True
        self.save()

    @classmethod
    def get_user_interests(cls, user):
        """Analyze user's watching patterns"""
        return (cls.objects
            .filter(user=user)
            .select_related('lesson', 'lesson__course')
            .annotate(
                watch_percentage=models.ExpressionWrapper(
                    models.F('current_time') * 100.0 / models.F('total_duration'),
                    output_field=models.FloatField()
                )
            )
        )

    @classmethod
    def get_most_engaged_content(cls, user):
        """Get content where user showed most engagement (watched >75%)"""
        return (cls.objects
            .filter(
                user=user,
                current_time__gt=0.75 * models.F('total_duration')
            )
            .select_related('lesson', 'lesson__course')
            .order_by('-last_watched')
        )

    @classmethod
    def get_course_completion_stats(cls, user):
        """Get stats about course progress"""
        from django.db.models import Count, Avg
        return (cls.objects
            .filter(user=user)
            .values('lesson__course__title')
            .annotate(
                lessons_watched=Count('lesson'),
                avg_completion=Avg(
                    models.ExpressionWrapper(
                        models.F('current_time') * 100.0 / models.F('total_duration'),
                        output_field=models.FloatField()
                    )
                )
            )
        )

    @classmethod
    def get_continue_watching(cls, user, limit=5):
        """Get lessons the user hasn't completed"""
        return (cls.objects
            .filter(
                user=user,
                completed=False,
                current_time__gt=0,  # Only include lessons they've started
                lesson__status=PublishStatus.PUBLISHED,
                lesson__course__status=PublishStatus.PUBLISHED
            )
            .select_related('lesson', 'lesson__course')
            .order_by('-last_watched')[:limit]
        )

    @classmethod
    def get_suggested_lessons(cls, user, limit=5):
        """Get suggested lessons based on user's watching patterns"""
        # Get courses user has watched
        watched_courses = (cls.objects
            .filter(user=user)
            .values_list('lesson__course', flat=True)
            .distinct()
        )
        
        # First, try to get unwatched lessons from courses they're already watching
        suggested = Lesson.objects.filter(
            status=PublishStatus.PUBLISHED,
            course__status=PublishStatus.PUBLISHED,
            course__id__in=watched_courses
        ).exclude(
            watchprogress__user=user
        ).select_related('course').order_by('order')[:limit]

        # If we need more suggestions, get lessons from other courses
        if suggested.count() < limit:
            remaining = limit - suggested.count()
            more_suggestions = Lesson.objects.filter(
                status=PublishStatus.PUBLISHED,
                course__status=PublishStatus.PUBLISHED
            ).exclude(
                course__id__in=watched_courses
            ).select_related('course').order_by('?')[:remaining]
            
            suggested = list(suggested) + list(more_suggestions)

        return suggested 