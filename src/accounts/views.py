from rest_framework import generics
from .models import Conversation
from .serializers import ConversationSerializer
from helpers.myclerk.decorators import api_login_required
from django.utils.decorators import method_decorator

@method_decorator(api_login_required, name='dispatch')
class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    # Remove this line since we're using Clerk's authentication
    # permission_classes = [permissions.IsAuthenticated]  

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)