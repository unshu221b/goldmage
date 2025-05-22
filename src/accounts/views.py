from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from helpers.myclerk.auth import ClerkAuthentication
from helpers.myclerk.decorators import api_login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .serializers import (
    AnalysisRequestSerializer,
    AnalysisResponseSerializer
)
import json
from openai import OpenAI

client = OpenAI()

@csrf_exempt
@method_decorator(api_login_required, name='dispatch')
class ConversationListCreateView(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer


    def get_queryset(self):
        print("User:", self.request.user)
        print("Is authenticated:", self.request.user.is_authenticated)
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
        
@csrf_exempt
@method_decorator(api_login_required, name='dispatch')
class AnalysisViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def analyze(self, request):
        # Validate request data
        serializer = AnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            messages = serializer.validated_data['messages']
            user_message = messages[-1]["text"] if messages else ""

            # Build the prompt
            prompt = (
                "Analyze the following chat message and generate a reaction, suggestions, and metrics. "
                "Return a JSON object with these fields:\n"
                "{\n"
                '  "reaction": "A brief emotional reaction to the message",\n'
                '  "suggestions": [\n'
                '    {\n'
                '      "id": "unique-id-1",\n'
                '      "suggestion": "first suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-2",\n'
                '      "suggestion": "second suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-3",\n'
                '      "suggestion": "third suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    },\n'
                '    {\n'
                '      "id": "unique-id-4",\n'
                '      "suggestion": "fourth suggestion text",\n'
                '      "style": "casual/professional/friendly/formal"\n'
                '    }\n'
                '  ],\n'
                '  "personality_metrics": {\n'
                '    "intelligence": number between 0-100 or null,\n'
                '    "charisma": number between 0-100 or null,\n'
                '    "strength": number between 0-100 or null,\n'
                '    "kindness": number between 0-100 or null\n'
                '  },\n'
                '  "emotion_metrics": {\n'
                '    "happiness": number between 0-100,\n'
                '    "sadness": number between 0-100,\n'
                '    "anger": number between 0-100,\n'
                '    "surprise": number between 0-100,\n'
                '    "fear": number between 0-100,\n'
                '    "disgust": number between 0-100,\n'
                '    "neutral": number between 0-100\n'
                '  }\n'
                "}\n\n"
                f"Message: \"{user_message}\""
            )

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert communication analyst and response generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
                temperature=0.7,
            )
            ai_content = response.choices[0].message.content.strip()

            # Parse OpenAI response
            try:
                openai_result = json.loads(ai_content)
            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if match:
                    openai_result = json.loads(match.group(0))
                else:
                    return Response(
                        {"error": "AI response was not valid JSON", "raw": ai_content}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # Validate and serialize the response
            response_data = {
                "reaction": openai_result.get("reaction", ""),
                "suggestions": openai_result.get("suggestions", []),
                "personality_metrics": openai_result.get("personality_metrics", {
                    "intelligence": None,
                    "charisma": None,
                    "strength": None,
                    "kindness": None
                }),
                "emotion_metrics": openai_result.get("emotion_metrics", {
                    "happiness": 50,
                    "sadness": 50,
                    "anger": 50,
                    "surprise": 50,
                    "fear": 50,
                    "disgust": 50,
                    "neutral": 50
                })
            }

            # Validate the response data
            response_serializer = AnalysisResponseSerializer(data=response_data)
            if not response_serializer.is_valid():
                return Response(
                    {"error": "Invalid response format", "details": response_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(response_serializer.validated_data)

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )