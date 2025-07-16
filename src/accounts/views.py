from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from .models import Conversation, Message, FavoriteConversation, CreditUsageHistory, Provider, ServiceOffering
from .serializers import ConversationSerializer, MessageSerializer, FavoriteConversationSerializer, ProviderSerializer, ServiceOfferingSerializer
from helpers.myclerk.auth import ClerkAuthentication
from helpers.myclerk.decorators import api_login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from django.http import Http404

from cfehome.views import send_error_email
import json
from openai import OpenAI
from helpers.vision.ocr import analyze_image_with_crop, extract_text_blocks_from_image
from helpers._mixpanel.client import mixpanel_client
import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger('goldmage')


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

                # Track new thread creation in Mixpanel
                mixpanel_client.track_api_event(
                    user_id=request.user.clerk_user_id,
                    event_name="new thread",
                    properties={
                        "conversation_id": str(conversation.uuid),
                        "title": conversation.title,
                        "messages_count": len(messages_data),
                        "user_email": request.user.email,
                        "ip_address": request.META.get("REMOTE_ADDR"),
                        "user_agent": request.META.get("HTTP_USER_AGENT"),
                    }
                )

                messages = []
                for msg_data in messages_data:
                    message = Message.objects.create(
                        conversation=conversation,
                        sender=msg_data.get('sender'),
                        input_type=msg_data.get('input_type', 'text'),
                        type=msg_data.get('type'),
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
            send_error_email(request, "BATCH_OPERATION_ERROR", str(e))  # Add this
            return Response({'error': str(e)}, status=400)
        
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
            send_error_email(request, "BATCH_OPERATION_ERROR", str(e))  # Add this
            return Response({'error': str(e)}, status=400)
        
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

        # Get conversation
        conversation_id = request.data.get('conversation_id')
        try:
            conversation = Conversation.objects.get(uuid=conversation_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=404)

        try:
            # Get messages to analyze
            messages_to_analyze = request.data.get('messages', [])
            
            # Format the messages for analysis
            conversation_history = "\n".join([
                f"{msg['sender']}: {msg['builder_data']['draft'][0]['text']}"
                for msg in messages_to_analyze
            ])

            prompt = (
                "Analyze the following conversation and generate a detailed emotional analysis. "
                "Return a JSON object with EXACTLY these fields:\n"
                "{\n"
                '  "emotions": [\n'  # Array of emotions for each message
                '    {\n'
                '      "primary": "Main emotion for this message",\n'
                '      "intensity": number between 0-100,\n'
                '      "secondary": ["Secondary emotion 1", "Secondary emotion 2"]\n'
                '    }\n'
                '  ],\n'
                '  "patterns": [\n'  # Array of patterns for each message
                '    "Pattern description for each message"\n'
                '  ],\n'
                '  "risks": [\n'  # Array of risks for each message
                '    "Risk level and description for each message"\n'
                '  ],\n'
                '  "communication": [\n'  # Array of communication styles for each message
                '    "Communication style for each message"\n'
                '  ],\n'
                '  "overallPattern": "Overall conversation pattern",\n'
                '  "riskLevel": "High/Medium/Low",\n'
                '  "confidence": number between 0-100,\n'
                '  "prediction": "Prediction about conversation outcome"\n'
                "}\n\n"
                "CRITICAL REQUIREMENTS:\n"
                "1. The number of items in each array (emotions, patterns, risks, communication) MUST match the number of lines in the conversation below EXACTLY.\n"
                "2. Process EVERY SINGLE LINE, including timestamps, duplicates, and system messages.\n"
                "3. For meaningless content (timestamps like '442', '4:41', single characters like '.', '...', or any non-communicative text), return this EXACT response:\n"
                "   - emotions: {\"primary\": \"wordless\", \"intensity\": 0, \"secondary\": []}\n"
                "   - patterns: \"Non-communicative content (timestamp/system message)\"\n"
                "   - risks: \"No risk - non-communicative content\"\n"
                "   - communication: \"Non-communicative\"\n"
                "4. For duplicate messages, analyze each occurrence separately.\n"
                "5. DO NOT skip, filter, or combine any messages.\n"
                "6. If you receive 12 messages, return exactly 12 items in each array.\n"
                "7. If you receive 15 messages, return exactly 15 items in each array.\n"
                "8. The array lengths must match the input message count PERFECTLY.\n"
                "9. Examples of meaningless content that should get the fixed response:\n"
                "   - '442', '4:41', '4:42PM', '12:30'\n"
                "   - '.', '...', '..', '...'\n"
                "   - Single characters or numbers\n"
                "   - Empty or whitespace-only messages\n"
                "   - System notifications or timestamps\n\n"
                f"Conversation:\n{conversation_history}"
            )

            # Call OpenAI
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are an expert communication analyst. Provide analysis in the exact JSON format requested. Each array should have the same length as the number of messages."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.7,
            )
            
            # Parse OpenAI response
            try:
                analysis_data = json.loads(response.choices[0].message.content)
                
                # Validate response structure
                required_fields = ['emotions', 'patterns', 'risks', 'communication', 
                                 'overallPattern', 'riskLevel', 'confidence', 'prediction']
                
                for field in required_fields:
                    if field not in analysis_data:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate array lengths match message count
                message_count = len(messages_to_analyze)
                for field in ['emotions', 'patterns', 'risks', 'communication']:
                    if len(analysis_data[field]) != message_count:
                        raise ValueError(f"Array length mismatch for {field}")
                
                # Validate emotion structure
                for emotion in analysis_data['emotions']:
                    if not all(k in emotion for k in ['primary', 'intensity', 'secondary']):
                        raise ValueError("Invalid emotion structure")
                    if not isinstance(emotion['secondary'], list):
                        raise ValueError("Secondary emotions must be a list")

            except json.JSONDecodeError:
                import re
                match = re.search(r'\{.*\}', response.choices[0].message.content, re.DOTALL)
                if match:
                    analysis_data = json.loads(match.group(0))
                else:
                    return Response(
                        {"error": "AI response was not valid JSON", "raw": response.choices[0].message.content}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

            # Deduct credit
            request.user.use_credit(
                event_type="deepfeel_hit",
                cost=1,
                kind="Monthly Credits",
                model_name="gpt-4.1"
            )
            
            # Only track if input_type is "text"
            input_type = request.data.get("input_type")
            if input_type == "text":
                mixpanel_client.track_api_event(
                    user_id=request.user.clerk_user_id,
                    event_name="text_builder_used",
                    properties={
                        "conversation_id": request.data.get("conversation_id"),
                        "messages_count": len(request.data.get("messages", [])),
                        "user_credits_before": request.user.credits + 1,
                        "user_email": request.user.email,
                        "ip_address": request.META.get("REMOTE_ADDR"),
                        "user_agent": request.META.get("HTTP_USER_AGENT"),
                    }
                )

            mixpanel_client.track_api_event(
                    user_id=request.user.clerk_user_id,
                    event_name="deepfeel_hit",
                    properties={
                        "conversation_id": request.data.get("conversation_id"),
                        "messages_count": len(request.data.get("messages", [])),
                        "user_credits_before": request.user.credits + 1,
                        "user_email": request.user.email,
                        "ip_address": request.META.get("REMOTE_ADDR"),
                        "user_agent": request.META.get("HTTP_USER_AGENT"),
                    }
                )
            # Return the analysis data directly
            return Response(analysis_data)

        except Exception as e:
            logger.error(f"Error in analyze: {str(e)}")
            send_error_email(request, "ANALYSIS_ERROR", str(e))
            return Response(
                {'error': str(e)}, 
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
        
        is_free_user = user.membership == 'FREE'
        
        return Response({
            'remaining_credits': user.credits,
            'reset_time': reset_time_iso,
            'is_out_of_credits': user.credits <= 0,
            'plan_type': user.membership,
            'total_credits': 200 if user.membership == 'PREMIUM' else 10,
            'total_usage_14d': user.total_usage_14d if is_free_user else 0,
            'is_thread_locked': user.is_thread_depth_locked if is_free_user else False,
            'days_until_refill': days_until_refill,
            'needs_extended_refresh': is_free_user and user.total_usage_14d >= 140,
            'is_extended_refresh': user.is_thread_depth_locked,
            'last_usage': user.last_usage_timestamp.isoformat() if user.last_usage_timestamp else None,
            'usage_limit': 140 if is_free_user else None,
            'daily_limit': 200 if user.membership == 'PREMIUM' else 10,
        })

    @action(detail=False, methods=['get'])
    def is_provider(self, request):
        return Response({'is_provider': request.user.is_provider})

    @action(detail=False, methods=['post'])
    def analyze_image(self, request):
        logger.info("DEBUG: Entered analyze_image view")  # Debug log

        # Check credits
        if not request.user.credits > 0:
            next_refill = request.user.get_daily_refill_time()
            return Response({
                'error': 'Insufficient credits',
                'remaining_credits': request.user.credits,
                'next_refill': next_refill,
                'is_thread_locked': request.user.is_thread_depth_locked,
            }, status=402)

        # Get image from request
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'No image provided'}, status=400)

        try:
            blocks = analyze_image_with_crop(image_file)
            # Deduct credit
            request.user.use_credit(
                event_type="image_upload",
                cost=1,
                kind="Monthly Credits",
                model_name="google-vision"
            )

            mixpanel_client.track_api_event(
                user_id=str(request.user.clerk_user_id),
                event_name="image_upload",
                properties={
                    "user_email": request.user.email,
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                    "image_size": request.FILES.get("image").size if request.FILES.get("image") else None,
                    "user_credits_before": request.user.credits + 1,
                    "conversation_id": request.data.get("conversation_id"),
                }
            )

            return Response({'blocks': blocks})
        except Exception as e:
            logger.error(f"Error in analyze_image: {e}")
            send_error_email(request, "IMAGE_ANALYSIS_ERROR", str(e))
            return Response({'error': str(e)}, status=500)

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

@method_decorator(api_login_required, name='dispatch')
class ChatViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        # Check credits
        if not request.user.credits > 0:
            next_refill = request.user.get_daily_refill_time()
            return Response({
                'error': 'Insufficient credits',
                'remaining_credits': request.user.credits,
                'next_refill': next_refill,
                'is_thread_locked': request.user.is_thread_depth_locked,
            }, status=402)

        # Get or create conversation
        conversation_uuid = request.data.get('conversation_uuid')
        message_content = request.data.get('message')
        
        try:
            with transaction.atomic():
                if conversation_uuid:
                    conversation = Conversation.objects.get(uuid=conversation_uuid, user=request.user)
                else:
                    # Create new conversation with initial title
                    conversation = Conversation.objects.create(
                        user=request.user,
                        title=message_content[:50] + "..." if len(message_content) > 50 else message_content
                    )

                # Create user message
                user_message = Message.objects.create(
                    conversation=conversation,
                    sender='user',
                    input_type='text',
                    text_content=message_content,
                    type='chat'
                )

                # Get conversation history for context
                conversation_history = Message.objects.filter(
                    conversation=conversation
                ).order_by('created_at')

                # Format conversation history for AI
                conversation_text = "\n".join([
                    f"{msg.sender}: {msg.text_content}"
                    for msg in conversation_history
                ])

                # Create a simple bond analyst system prompt
                system_prompt = "You are a bond analyst assigned to help understand relationship patterns. Your job is to:\n\n"
                system_prompt += "Help the user name patterns in their relationship\n"
                system_prompt += "Reflect on whether those patterns are healthy, manipulative, or confusing\n"
                system_prompt += "Offer framing questions but do not tell them what to feel or do\n\n"
                system_prompt += "**CONVERSATION HISTORY:**\n"
                system_prompt += conversation_text if conversation_text else "No previous messages"
                system_prompt += "\n\nRemember: You are analyzing patterns and helping the user understand their relationship dynamics. Do not tell them what to feel or do - help them see patterns and ask thoughtful questions."

                # Format messages for OpenAI
                messages = [
                    {"role": "system", "content": system_prompt},
                ]
                
                for msg in conversation_history:
                    role = "user" if msg.sender == "user" else "assistant"
                    messages.append({
                        "role": role,
                        "content": msg.text_content
                    })

                # Call OpenAI
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.7,
                )

                # Create AI response message
                ai_response = response.choices[0].message.content
                ai_message = Message.objects.create(
                    conversation=conversation,
                    sender='ai',
                    input_type='text',
                    text_content=ai_response,
                    type='chat'
                )

                # Deduct credit
                request.user.use_credit(
                    event_type="chat",
                    cost=1,
                    kind="Monthly Credits",
                    model_name="gpt-4o"
                )

                mixpanel_client.track_api_event(
                    user_id=request.user.clerk_user_id,
                    event_name="chat",
                    properties={
                        "conversation_uuid": request.data.get("conversation_uuid"),
                        "message_length": len(request.data.get("message", "")),
                        "is_new_conversation": not request.data.get("conversation_uuid"),
                        "user_credits_before": request.user.credits + 1,
                        "user_email": request.user.email,
                        "ip_address": request.META.get("REMOTE_ADDR"),
                        "user_agent": request.META.get("HTTP_USER_AGENT"),
                    }
                )
                return Response({
                    'conversation_uuid': conversation.uuid,
                    'messages': [
                        MessageSerializer(user_message).data,
                        MessageSerializer(ai_message).data
                    ]
                })

        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=404)
        except Exception as e:
            send_error_email(request, "CHAT_ERROR", str(e))
            return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def credit_usage_history(request):
    history = CreditUsageHistory.objects.filter(user=request.user)
    data = [
        {
            "event_type": h.event_type,
            "cost": str(h.cost),
            "date": h.date.strftime("%B %d, %Y"),
            "kind": h.kind,
            "model": h.model,
        }
        for h in history
    ]
    return Response(data)

@method_decorator(api_login_required, name='dispatch')
class ProviderViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def submit_provider(self, request):
        try:
            logger.info(f"Raw request body: {request.body}")

            provider_data = request.data.get('provider')
            offering_data = request.data.get('service_offering')

            # 1. Create Provider (or get existing for this user+name)
            provider_serializer = ProviderSerializer(data=provider_data)
            if provider_serializer.is_valid():
                provider = provider_serializer.save(user=request.user)
                
                # Set is_provider to True if not already
                if not request.user.is_provider:
                    request.user.is_provider = True
                    request.user.save()
                logger.info(f"Provider data: {provider_data}")
                logger.info(f"Service offering data: {offering_data}")
            else:
                logger.info(f"Provider serializer errors: {provider_serializer.errors}")
                return Response(provider_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            # 2. Create ServiceOffering
            offering_serializer = ServiceOfferingSerializer(data=offering_data)
            if offering_serializer.is_valid():
                offering = offering_serializer.save(provider=provider)
                return Response({
                    'provider_id': provider.id,
                    'offering_id': offering.id,
                    'message': 'Listing submitted!'
                }, status=status.HTTP_201_CREATED)
            else:
                # If provider was just created, you may want to delete it if offering fails
                logger.info(f"Offering serializer errors: {offering_serializer.errors}")
                provider.delete()
                return Response(offering_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.info(f"Exception in submit_provider: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)