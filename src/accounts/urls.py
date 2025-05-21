from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ConversationListCreateView


# Create a router
router = DefaultRouter()
router.register(r'conversations', ConversationListCreateView, basename='conversation')

urlpatterns = [
    # Your existing URLs
    # path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
] + router.urls