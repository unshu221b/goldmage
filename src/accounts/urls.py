from django.urls import path
from .views import ConversationListCreateView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list-create'),
]