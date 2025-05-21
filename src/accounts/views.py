from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

class ConversationListCreateView(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        # Get data from request
        title = request.data.get('title')
        messages_data = request.data.get('messages', [])

        # Create conversation
        conversation = Conversation.objects.create(
            title=title,
            user=request.user
        )

        # Create all messages
        messages = []
        for msg_data in messages_data:
            message = Message.objects.create(
                conversation=conversation,
                sender=msg_data['sender'],
                input_type='text',  # or get from msg_data
                text_content=msg_data['text_content']
            )
            messages.append(message)

        # Return the created data
        return Response({
            'conversation': ConversationSerializer(conversation).data,
            'messages': MessageSerializer(messages, many=True).data
        }, status=status.HTTP_201_CREATED)