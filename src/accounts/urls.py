from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ConversationListCreateView, AnalysisViewSet


# Create a router
router = DefaultRouter()
router.register(r'conversations', ConversationListCreateView, basename='conversation')
router.register(r'analysis', AnalysisViewSet, basename='analysis')

urlpatterns = [
    # Your existing URLs
    # path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
] + router.urls