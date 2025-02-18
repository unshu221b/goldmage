import helpers
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
import logging
from cloudinary.utils import cloudinary_url
from django.views.decorators.http import require_POST
import json

from . import services
from .models import Course, Lesson, PublishStatus, WatchProgress

logger = logging.getLogger(__name__)

def course_list_view(request):
    queryset = services.get_publish_courses()
    context = {
        "object_list": queryset
    }
    template_name = "courses/list.html"
    if request.htmx:
        template_name = "courses/snippets/list-display.html"
        context['queryset'] = queryset[:3]
    return render(request, template_name, context)


def course_detail_view(request, course_id=None, *args, **kwarg):
    course_obj = services.get_course_detail(course_id=course_id)
    if course_obj is None:
        raise Http404
        
    lessons_queryset = services.get_course_lessons(course_obj)
    
    # Debug print
    print(f"Number of lessons: {lessons_queryset.count()}")
    
    # Get watch progress for all lessons
    if request.user.is_authenticated:
        progress_dict = WatchProgress.objects.filter(
            user=request.user,
            lesson__in=lessons_queryset
        ).values('lesson_id', 'current_time', 'total_duration')
        
        # Debug print
        print(f"Progress data: {progress_dict}")
        
        # Add progress to each lesson
        for lesson in lessons_queryset:
            progress = next((p for p in progress_dict if p['lesson_id'] == lesson.id), None)
            if progress and progress['total_duration']:
                lesson.progress = (progress['current_time'] / progress['total_duration']) * 100
            else:
                lesson.progress = 0
    
    context = {
        "object": course_obj,
        "lessons_queryset": lessons_queryset[:5],  # Limit to 5 items per slide
    }
    
    # Debug print
    print(f"Context: {context}")
    
    return render(request, "courses/detail.html", context)


def lesson_detail_view(request, course_id=None, lesson_id=None, *args, **kwargs):
    lesson_obj = services.get_lesson_detail(
        course_id=course_id,
        lesson_id=lesson_id
    )
    if lesson_obj is None:
        raise Http404

    if lesson_obj.requires_email and not request.user.is_authenticated:
        request.session['next_url'] = request.path
        return redirect('login')
        
    # Get next lessons for the "Watch Next" section
    next_lessons = Lesson.objects.filter(
        course=lesson_obj.course,
        order__gt=lesson_obj.order,
        status=PublishStatus.PUBLISHED
    ).order_by('order')[:3]

    context = {
        "object": lesson_obj,
        "next_lessons": next_lessons
    }
    
    if not lesson_obj.is_coming_soon and lesson_obj.has_video:
        template_name = "courses/lesson.html"
        video_embed_html = helpers.get_cloudinary_video_object(
            lesson_obj, 
            field_name='video',
            as_html=True,
            width=1250
        )
        context['video_embed'] = video_embed_html
    else:
        template_name = "courses/lesson-coming-soon.html"
        
    return render(request, template_name, context)

def get_thumbnails(request, category):
    try:
        if category == 'Home':
            lessons = Lesson.objects.filter(featured=True)
        else:
            lessons = Lesson.objects.filter(category=category)
            
        thumbnails = [{
            'title': lesson.title,
            'lesson_url': lesson.get_absolute_url(),
            'image_url': lesson.get_thumbnail,
            'duration': str(lesson.duration),
            'progress': lesson.get_progress(request.user),
            'subtitle': lesson.subtitle
        } for lesson in lessons]
        
        return JsonResponse(thumbnails, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
def update_progress(request):
    data = json.loads(request.body)
    lesson_id = data.get('lesson_id')
    current_time = data.get('current_time')
    total_duration = data.get('total_duration')

    if not all([lesson_id, current_time, total_duration]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    try:
        lesson = Lesson.objects.get(id=lesson_id)
        progress, created = WatchProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={
                'total_duration': total_duration
            }
        )
        progress.current_time = current_time
        if not created:
            progress.total_duration = total_duration
        progress.save()
        
        return JsonResponse({
            'progress': round((current_time / total_duration) * 100)
        })
    except Lesson.DoesNotExist:
        return JsonResponse({'error': 'Lesson not found'}, status=404)