from django.urls import path
from django.http import JsonResponse

from . import views

app_name = 'courses'

# Debug view to test routing
def test_view(request):
    return JsonResponse({"message": "Test route works!"})

urlpatterns = [
    # API endpoints first (more specific)
    path('api/watch-progress/', views.update_progress, name='watch_progress'),
    path('api/watch-progress/<str:lesson_id>/', views.get_progress, name='get_progress'),
    
    # Test route
    path('test/', test_view, name='test'),
    
    # Your existing course routes (more general)
    path('<slug:course_id>/lessons/<slug:lesson_id>/', views.lesson_detail_view, name='lesson_detail'),
    path('<slug:course_id>/', views.course_detail_view, name='course_detail'),
    path("", views.course_list_view),
    path('lesson/<str:lesson_id>/like/', views.toggle_like, name='toggle_like'),
]
