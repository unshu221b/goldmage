from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message, ConversationAnalysis
from .serializers import ConversationSerializer, MessageSerializer, ConversationAnalysisSerializer
from helpers.myclerk.auth import ClerkAuthentication
from helpers.myclerk.decorators import api_login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction

from .serializers import (
    AnalysisRequestSerializer,
    AnalysisResponseSerializer
)
import json
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@method_decorator(api_login_required, name='dispatch')
class ConversationListCreateView(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        # Get data from request
        title = request.data.get('title')
        messages_data = request.data.get('messages', [])
        analysis_data = request.data.get('analysis', {})

        try:
            with transaction.atomic():
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
                        input_type='text',
                        text_content=msg_data['text_content']
                    )
                    messages.append(message)

                # Create analysis if analysis data is provided
                analysis = None
                if analysis_data:
                    analysis = ConversationAnalysis.objects.create(
                        conversation=conversation,
                        reaction=analysis_data.get('reaction'),
                        suggestions=analysis_data.get('suggestions'),
                        personality_metrics=analysis_data.get('personality_metrics'),
                        emotion_metrics=analysis_data.get('emotion_metrics'),
                        dominant_emotion=analysis_data.get('dominant_emotion')
                    )

                # Return the created data
                response_data = {
                    'conversation': ConversationSerializer(conversation).data,
                    'messages': MessageSerializer(messages, many=True).data
                }
                
                if analysis:
                    response_data['analysis'] = ConversationAnalysisSerializer(analysis).data

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=['put', 'patch'])
    def batch_update(self, request, pk=None):
        """
        Update an existing conversation, its messages, and analysis
        """
        try:
            with transaction.atomic():
                # Get the existing conversation
                conversation = self.get_queryset().get(pk=pk)
                
                # Update conversation title if provided
                if 'title' in request.data:
                    conversation.title = request.data['title']
                    conversation.save()

                # Update messages if provided
                if 'messages' in request.data:
                    # Delete existing messages
                    conversation.messages.all().delete()
                    
                    # Create new messages
                    messages = []
                    for msg_data in request.data['messages']:
                        message = Message.objects.create(
                            conversation=conversation,
                            sender=msg_data['sender'],
                            input_type='text',
                            text_content=msg_data['text_content']
                        )
                        messages.append(message)

                # Update analysis if provided
                if 'analysis' in request.data:
                    analysis_data = request.data['analysis']
                    
                    # Delete existing analysis if it exists
                    ConversationAnalysis.objects.filter(conversation=conversation).delete()
                    
                    # Create new analysis
                    analysis = ConversationAnalysis.objects.create(
                        conversation=conversation,
                        reaction=analysis_data.get('reaction'),
                        suggestions=analysis_data.get('suggestions'),
                        personality_metrics=analysis_data.get('personality_metrics'),
                        emotion_metrics=analysis_data.get('emotion_metrics'),
                        dominant_emotion=analysis_data.get('dominant_emotion')
                    )

                # Return updated data
                response_data = {
                    'conversation': ConversationSerializer(conversation).data,
                    'messages': MessageSerializer(conversation.messages.all(), many=True).data
                }

                # Add analysis data if it exists
                analysis = ConversationAnalysis.objects.filter(conversation=conversation).first()
                if analysis:
                    response_data['analysis'] = ConversationAnalysisSerializer(analysis).data

                return Response(response_data)

        except Conversation.DoesNotExist:
            return Response(
                {'detail': 'Conversation not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        

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