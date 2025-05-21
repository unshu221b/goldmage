from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from helpers.myclerk.auth import ClerkAuthentication

class ConversationListCreateView(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    authentication_classes = [ClerkAuthentication]
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
    
    @action(detail=True, methods=['put', 'patch'])
    def batch_update(self, request, pk=None):
        """
        Update an existing conversation and its messages
        """
        try:
            # Get the existing conversation
            conversation = self.get_queryset().get(pk=pk)
            
            # Update conversation title if provided
            if 'title' in request.data:
                conversation.title = request.data['title']
                conversation.save()

            # Update messages if provided
            if 'messages' in request.data:
                # Optional: Delete existing messages if you want to replace them
                # conversation.messages.all().delete()
                
                # Update or create messages
                updated_messages = []
                for msg_data in request.data['messages']:
                    if 'id' in msg_data:
                        # Update existing message
                        message = conversation.messages.get(id=msg_data['id'])
                        message.text_content = msg_data['text_content']
                        message.sender = msg_data['sender']
                        message.save()
                    else:
                        # Create new message
                        message = Message.objects.create(
                            conversation=conversation,
                            sender=msg_data['sender'],
                            input_type='text',
                            text_content=msg_data['text_content']
                        )
                    updated_messages.append(message)

            # Return updated data
            return Response({
                'conversation': ConversationSerializer(conversation).data,
                'messages': MessageSerializer(conversation.messages.all(), many=True).data
            })

        except Conversation.DoesNotExist:
            return Response(
                {'detail': 'Conversation not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )