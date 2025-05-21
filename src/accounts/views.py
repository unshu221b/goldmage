from rest_framework import generics
from .models import Conversation
from .serializers import ConversationSerializer


class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    # Remove this line since we're using Clerk's authentication
    # permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)