from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Lesson, Course
from cfehome.views import invalidate_featured_cache, invalidate_user_cache

@receiver(post_save, sender=Lesson)
def invalidate_lesson_cache(sender, instance, **kwargs):
    """Invalidate relevant caches when a lesson is updated"""
    invalidate_featured_cache()
    # Invalidate cache for all users who have interacted with this lesson
    for progress in instance.watchprogress_set.all():
        invalidate_user_cache(progress.user.id)

@receiver(post_save, sender=Course)
def invalidate_course_cache(sender, instance, **kwargs):
    """Invalidate relevant caches when a course is updated"""
    invalidate_featured_cache()
    # Invalidate cache for all lessons in this course
    for lesson in instance.lesson_set.all():
        for progress in lesson.watchprogress_set.all():
            invalidate_user_cache(progress.user.id) 