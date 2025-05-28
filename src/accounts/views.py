from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message, ConversationAnalysis, FavoriteConversation
from .serializers import ConversationSerializer, MessageSerializer, ConversationAnalysisSerializer, AnalysisRequestSerializer, FavoriteConversationSerializer
from helpers.myclerk.auth import ClerkAuthentication
from helpers.myclerk.decorators import api_login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import Http404

import json
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@method_decorator(api_login_required, name='dispatch')
class ConversationListCreateView(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    lookup_field = 'uuid'  # Add this line to use uuid instead of id

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def get_object(self):
        # Get the uuid from the URL
        uuid = self.kwargs.get('uuid')  # Change 'pk' to 'uuid'
        # Try to get the conversation by uuid
        try:
            return self.get_queryset().get(uuid=uuid)
        except Conversation.DoesNotExist:
            raise Http404("No conversation found with the given UUID")

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
    def batch_update(self, request, uuid=None):
        """
        Update an existing conversation, its messages, and analysis
        """
        try:
            with transaction.atomic():
                # Get the existing conversation
                conversation = self.get_queryset().get(uuid=uuid)
                
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
        
    @action(detail=False, methods=['get'])
    def history(self, request):
        conversations = (
            self.get_queryset()
            .order_by('-created_at')
            .values('uuid', 'title', 'created_at')
        )
        data = [
            {
                'id': str(conv['uuid']),
                'title': conv['title'],
                'date': conv['created_at'].isoformat()
            }
            for conv in conversations
        ]
        return Response(data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

@method_decorator(api_login_required, name='dispatch')
class AnalysisViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def analyze(self, request):
        # Check credits
        if not request.user.credits > 0:
            next_refill = request.user.get_daily_refill_time()
            return Response({
                'error': 'Insufficient credits',
                'remaining_credits': request.user.credits,
                'next_refill': next_refill,
                'is_thread_locked': request.user.is_thread_depth_locked,
                'upgrade_url': '/dashboard/upgrade'
            }, status=402)

        # Check thread depth lock
        if request.user.is_thread_depth_locked:
            return Response({
                'error': 'Thread depth limit reached',
                'message': 'You have reached the 14-day usage limit. Please wait for the cooldown period.',
                'remaining_credits': request.user.credits,
                'next_refill': request.user.get_daily_refill_time()
            }, status=429)

        # Validate request data
        serializer = AnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            messages = serializer.validated_data['messages']
            
            # Format the entire conversation history
            conversation_history = "\n".join([
                f"{msg['sender']}: {msg['text']}"
                for msg in messages
            ])

            # Build the prompt
            prompt = (
                "Analyze the following conversation and generate a reaction, suggestions, and metrics. "
                "Consider the entire conversation context, not just individual messages. "
                "Return a JSON object with these fields:\n"
                "{\n"
                '  "reaction": "A brief emotional reaction to the overall conversation",\n'
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
                '  },\n'
                '  "dominant_emotion": "The emotion with the highest score from emotion_metrics"\n'
                "}\n\n"
                f"Conversation:\n{conversation_history}"
            )

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert communication analyst and response generator. Analyze the entire conversation context to provide meaningful insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,  # Increased token limit for longer conversations
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
                }),
                "dominant_emotion": max(openai_result.get("emotion_metrics", {}).items(), key=lambda x: x[1])[0]
            }

            # Validate the response data
            response_serializer = ConversationAnalysisSerializer(data=response_data)
            if not response_serializer.is_valid():
                return Response(
                    {"error": "Invalid response format", "details": response_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Deduct one credit after successful analysis
            request.user.use_credit()

            return Response(response_data)

        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def status(self, request):
        user = request.user
        user.check_and_refill_credits()
        
        reset_time = user.get_daily_refill_time()
        reset_time_iso = reset_time.isoformat() if reset_time else None
        
        now = timezone.now()
        days_until_refill = (reset_time - now).days if reset_time else None
        
        is_free_user = user.membership == 'free'
        
        return Response({
            'remaining_credits': user.credits,
            'reset_time': reset_time_iso,
            'is_out_of_credits': user.credits <= 0,
            'plan_type': user.membership,
            'total_credits': 200 if user.membership == 'premium' else 10,
            'total_usage_14d': user.total_usage_14d if is_free_user else 0,
            'is_thread_locked': user.is_thread_depth_locked if is_free_user else False,
            'days_until_refill': days_until_refill,
            'needs_extended_refresh': is_free_user and user.total_usage_14d >= 140,
            'is_extended_refresh': user.is_thread_depth_locked,
            'last_usage': user.last_usage_timestamp.isoformat() if user.last_usage_timestamp else None,
            'usage_limit': 140 if is_free_user else None,
            'daily_limit': 200 if user.membership == 'premium' else 10
        })

@method_decorator(api_login_required, name='dispatch')
class FavoriteConversationViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteConversationSerializer
    
    def get_queryset(self):
        return FavoriteConversation.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        conversation_uuid = self.request.data.get('conversation_uuid')
        try:
            conversation = Conversation.objects.get(uuid=conversation_uuid, user=self.request.user)
            serializer.save(user=self.request.user, conversation=conversation)
        except Conversation.DoesNotExist:
            raise Http404("Conversation not found")
    
    @action(detail=False, methods=['get'])
    def list_favorites(self, request):
        favorites = self.get_queryset().select_related('conversation')
        serializer = self.get_serializer(favorites, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def toggle_favorite(self, request):
        conversation_uuid = request.data.get('conversation_uuid')
        try:
            conversation = Conversation.objects.get(uuid=conversation_uuid, user=request.user)
            favorite, created = FavoriteConversation.objects.get_or_create(
                user=request.user,
                conversation=conversation
            )
            
            if not created:
                favorite.delete()
                return Response({'status': 'removed'})
            
            serializer = self.get_serializer(favorite)
            return Response(serializer.data)
            
        except Conversation.DoesNotExist:
            raise Http404("Conversation not found")