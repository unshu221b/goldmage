from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ConversationListCreateView, AnalysisViewSet, FavoriteConversationViewSet, ChatViewSet, credit_usage_history


# Create a router
router = DefaultRouter()
router.register(r'conversations', ConversationListCreateView, basename='conversation')
router.register(r'analysis', AnalysisViewSet, basename='analysis')
router.register(r'favorites', FavoriteConversationViewSet, basename='favorite')
router.register(r'chat', ChatViewSet, basename='chat')

urlpatterns = [
    # Your existing URLs
    # Add direct path for credits status
    path('credits/status/', AnalysisViewSet.as_view({'get': 'status'}), name='credits-status'),
    path('history/', ConversationListCreateView.as_view({'get': 'history'}), name='history'),
    path('credits/history/', credit_usage_history, name='credit-usage-history'),
] + router.urls