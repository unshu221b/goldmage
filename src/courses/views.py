import helpers
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
import logging
from cloudinary.utils import cloudinary_url

from . import services
from .models import Course, Lesson

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
    context = {
        "object": course_obj,
        "lessons_queryset": lessons_queryset,
    }
    # return JsonResponse({"data": course_obj.id, 'lesson_ids': [x.path for x in lessons_queryset] })
    return render(request, "courses/detail.html", context)


def lesson_detail_view(request, course_id=None, lesson_id=None, *args, **kwargs):
    print(course_id, lesson_id)
    lesson_obj = services.get_lesson_detail(
        course_id=course_id,
        lesson_id=lesson_id
    )
    if lesson_obj is None:
        raise Http404

    # Check if user is authenticated instead of email_id
    if lesson_obj.requires_email and not request.user.is_authenticated:
        request.session['next_url'] = request.path
        return redirect('login')  # Use your login URL name here
        
    template_name = "courses/lesson-coming-soon.html"
    context = {
        "object": lesson_obj
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
            'image_url': lesson.thumbnail.url,
            'duration': str(lesson.duration),
            'progress': lesson.get_progress(request.user),
            'subtitle': lesson.subtitle
        } for lesson in lessons]
        
        return JsonResponse(thumbnails, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)