from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ConversationListCreateView, AnalysisViewSet, ChatViewSet, credit_usage_history, ProviderViewSet

# Create a router
router = DefaultRouter()
router.register(r'conversations', ConversationListCreateView, basename='conversation')
router.register(r'analysis', AnalysisViewSet, basename='analysis')
router.register(r'chat', ChatViewSet, basename='chat')
router.register(r'providers', ProviderViewSet, basename='provider')

urlpatterns = [
    # Your existing URLs
    # Add direct path for credits status
    path('credits/status/', AnalysisViewSet.as_view({'get': 'status'}), name='credits-status'),
    path('history/', ConversationListCreateView.as_view({'get': 'history'}), name='history'),
    path('credits/history/', credit_usage_history, name='credit-usage-history'),
] + router.urls