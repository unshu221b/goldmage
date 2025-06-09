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

        try:
            with transaction.atomic():
                conversation = Conversation.objects.create(
                    title=title,
                    user=request.user
                )

                messages = []
                for msg_data in messages_data:
                    message = Message.objects.create(
                        conversation=conversation,
                        sender=msg_data.get('sender'),
                        input_type=msg_data.get('input_type', 'text'),
                        text_content=msg_data.get('text_content', ''),
                        image=msg_data.get('image'),
                        builder_data=msg_data.get('builder_data'),
                    )
                    messages.append(message)

                response_data = {
                    'conversation': ConversationSerializer(conversation).data,
                    'messages': MessageSerializer(messages, many=True).data
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=['put', 'patch'])
    def batch_update(self, request, uuid=None):

        try:
            with transaction.atomic():
                # Get the existing conversation
                conversation = self.get_queryset().get(uuid=uuid)
                
                # Update conversation title if provided
                if 'title' in request.data:
                    conversation.title = request.data['title']
                    conversation.save()

                if 'messages' in request.data:
                    # Optionally: don't delete all messages, just add new ones
                    for msg_data in request.data['messages']:
                        Message.objects.create(
                            conversation=conversation,
                            sender=msg_data.get('sender'),
                            input_type=msg_data.get('input_type', 'text'),
                            text_content=msg_data.get('text_content', ''),
                            builder_data=msg_data.get('builder_data'),
                            type=msg_data.get('type'),
                            analysis_data=msg_data.get('analysis_data'),
                        )

                # Return the updated conversation with all its related data
                serializer = self.get_serializer(conversation)
                return Response(serializer.data)

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

            prompt = (
                "Analyze the following conversation and generate a detailed emotional analysis. "
                "Consider each message and the overall conversation context. "
                "Return a JSON object with these fields:\n"
                "{\n"
                '  "emotions": [\n'  # Array of emotions for each message
                '    {\n'
                '      "primary": "Main emotion for this message",\n'
                '      "intensity": number between 0-100,\n'
                '      "secondary": ["Secondary emotion 1", "Secondary emotion 2"]\n'
                '    }\n'
                '    // Generate one object for each message in the conversation\n'
                '  ],\n'
                '  "patterns": [\n'  # Array of patterns for each message
                '    // Generate one pattern for each message\n'
                '  ],\n'
                '  "risks": [\n'  # Array of risks for each message
                '    // Generate one risk level for each message\n'
                '  ],\n'
                '  "communication": [\n'  # Array of communication styles for each message
                '    // Generate one style for each message\n'
                '  ],\n'
                '  "overallPattern": "Overall conversation pattern",\n'
                '  "riskLevel": "High/Medium/Low",\n'
                '  "confidence": number between 0-100,\n'
                '  "prediction": "Prediction about conversation outcome"\n'
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
                "emotions": openai_result.get("emotions", []),
                "patterns": openai_result.get("patterns", []),
                "risks": openai_result.get("risks", []),
                "communication": openai_result.get("communication", []),
                "overallPattern": openai_result.get("overallPattern", ""),
                "riskLevel": openai_result.get("riskLevel", "Medium"),
                "confidence": openai_result.get("confidence", 50),
                "prediction": openai_result.get("prediction", "")
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