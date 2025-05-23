from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ConversationListCreateView, AnalysisViewSet


# Create a router
router = DefaultRouter()
router.register(r'conversations', ConversationListCreateView, basename='conversation')
router.register(r'analysis', AnalysisViewSet, basename='analysis')

urlpatterns = [
    # Your existing URLs
    # Add direct path for credits status
    path('credits/status/', AnalysisViewSet.as_view({'get': 'status'}), name='credits-status'),
] + router.urls