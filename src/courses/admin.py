import helpers
from cloudinary import CloudinaryImage
from django.contrib import admin
from django.utils.html import format_html
# Register your models here.
from .models import Course, Lesson, LessonLike


class LessonInline(admin.StackedInline):
    model = Lesson
    readonly_fields = [
        'public_id', 
        'updated', 
        'display_image',
        'display_video',
    ]
    extra = 0

    def display_image(self, obj, *args, **kwargs):
        url = helpers.get_cloudinary_image_object(
            obj, 
            field_name='thumbnail',
            width=200
        )
        return format_html(f"<img src={url} />")

    display_image.short_description = "Current Image"

    def display_video(self, obj, *args, **kwargs):
        video_embed_html = helpers.get_cloudinary_video_object(
            obj, 
            field_name='video',
            as_html=True,
            width=550
        )
        return video_embed_html

    display_video.short_description = "Current Video"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ['title', 'status', 'access']
    list_filter = ['status', 'access']
    fields = ['public_id', 'title', 'description', 'status', 'image', 'access', 'display_image']
    readonly_fields = ['public_id', 'display_image']

    def display_image(self, obj, *args, **kwargs):
        url = helpers.get_cloudinary_image_object(
            obj, 
            field_name='image',
            width=200
        )
        return format_html(f"<img src={url} />")

    display_image.short_description = "Current Image"


@admin.register(LessonLike)
class LessonLikeAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'user', 'created_at')
    list_filter = ('lesson', 'created_at')
    search_fields = ('lesson__title', 'user__email')
    date_hierarchy = 'created_at'


# admin.site.register(Course, CourseAdmin)