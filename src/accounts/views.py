from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Conversation, Message, FavoriteConversation
from .serializers import ConversationSerializer, MessageSerializer, FavoriteConversationSerializer
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
            request.user.use_credit()
            
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
            request.user.use_credit()

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
    def _extract_person_name(self, conversation_title):
        """Extract person name from conversation title or return default"""
        # Simple extraction - could be enhanced with NLP
        if conversation_title and len(conversation_title) > 0:
            # Remove common suffixes and clean up
            title = conversation_title.replace("...", "").strip()
            if title:
                return title
        return "this person"

    def _build_person_library(self, user, person_name):
        """Build a comprehensive library of emotional patterns for a specific person"""
        # Get all conversations that might be about this person
        all_conversations = Conversation.objects.filter(user=user)
        
        person_library = {
            'emotional_triggers': [],
            'communication_patterns': [],
            'risk_indicators': [],
            'behavioral_trends': [],
            'relationship_dynamics': [],
            'significant_events': []
        }
        
        # Collect analysis data from all conversations
        for conversation in all_conversations:
            messages_with_analysis = Message.objects.filter(
                conversation=conversation,
                analysis_data__isnull=False
            ).exclude(analysis_data={})
            
            for message in messages_with_analysis:
                if message.analysis_data and isinstance(message.analysis_data, dict):
                    # Extract emotions
                    if 'emotions' in message.analysis_data:
                        for emotion in message.analysis_data['emotions']:
                            person_library['emotional_triggers'].append({
                                'emotion': emotion.get('primary', 'Unknown'),
                                'intensity': emotion.get('intensity', 0),
                                'secondary': emotion.get('secondary', []),
                                'context': message.text_content[:100] + "..." if message.text_content else "No context",
                                'date': message.created_at.isoformat()
                            })
                    
                    # Extract patterns
                    if 'patterns' in message.analysis_data:
                        for pattern in message.analysis_data['patterns']:
                            person_library['communication_patterns'].append({
                                'pattern': pattern,
                                'context': message.text_content[:100] + "..." if message.text_content else "No context",
                                'date': message.created_at.isoformat()
                            })
                    
                    # Extract risks
                    if 'risks' in message.analysis_data:
                        for risk in message.analysis_data['risks']:
                            person_library['risk_indicators'].append({
                                'risk': risk,
                                'context': message.text_content[:100] + "..." if message.text_content else "No context",
                                'date': message.created_at.isoformat()
                            })
                    
                    # Extract communication styles
                    if 'communication' in message.analysis_data:
                        for style in message.analysis_data['communication']:
                            person_library['behavioral_trends'].append({
                                'style': style,
                                'context': message.text_content[:100] + "..." if message.text_content else "No context",
                                'date': message.created_at.isoformat()
                            })
                    
                    # Extract overall patterns
                    if 'overallPattern' in message.analysis_data:
                        person_library['relationship_dynamics'].append({
                            'pattern': message.analysis_data['overallPattern'],
                            'risk_level': message.analysis_data.get('riskLevel', 'Unknown'),
                            'confidence': message.analysis_data.get('confidence', 0),
                            'prediction': message.analysis_data.get('prediction', ''),
                            'date': message.created_at.isoformat()
                        })
        
        return person_library

    def _get_latest_analysis(self, conversation):
        """Get the most recent analysis data for the current conversation"""
        latest_analysis = Message.objects.filter(
            conversation=conversation,
            analysis_data__isnull=False
        ).exclude(analysis_data={}).order_by('-created_at').first()
        
        if latest_analysis and latest_analysis.analysis_data:
            return latest_analysis.analysis_data
        return None

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

                # Extract person name from conversation title
                person_name = self._extract_person_name(conversation.title)
                
                # Build comprehensive person library
                person_library = self._build_person_library(request.user, person_name)
                
                # Get latest analysis data for this conversation
                latest_analysis = self._get_latest_analysis(conversation)

                # Get conversation history for context
                conversation_history = Message.objects.filter(
                    conversation=conversation
                ).order_by('created_at')

                # Format conversation history for AI
                conversation_text = "\n".join([
                    f"{msg.sender}: {msg.text_content}"
                    for msg in conversation_history
                ])

                # Create the bond analyst system prompt with person library
                system_prompt = f"""You are a bond analyst assigned to help understand {person_name}. You have access to a comprehensive library of their emotional patterns and behaviors. Your job is to:

Help the user name patterns in their relationship with {person_name}
Reflect on whether those patterns are healthy, manipulative, or confusing
Offer framing questions but do not tell them what to feel or do

**PERSON LIBRARY - {person_name.upper()}**

**Emotional Triggers (Last 10):**
{chr(10).join([f"- {trigger['emotion']} (intensity: {trigger['intensity']}) - {trigger['date'][:10]}" for trigger in person_library['emotional_triggers'][-10:]]) if person_library['emotional_triggers'] else "No emotional data yet"}

**Communication Patterns (Last 5):**
{chr(10).join([f"- {pattern['pattern']} - {pattern['date'][:10]}" for pattern in person_library['communication_patterns'][-5:]]) if person_library['communication_patterns'] else "No patterns detected yet"}

**Risk Indicators (Last 5):**
{chr(10).join([f"- {risk['risk']} - {risk['date'][:10]}" for risk in person_library['risk_indicators'][-5:]]) if person_library['risk_indicators'] else "No risks identified yet"}

**Behavioral Trends (Last 5):**
{chr(10).join([f"- {trend['style']} - {trend['date'][:10]}" for trend in person_library['behavioral_trends'][-5:]]) if person_library['behavioral_trends'] else "No behavioral data yet"}

**Relationship Dynamics (Last 3):**
{chr(10).join([f"- {dynamic['pattern']} (Risk: {dynamic['risk_level']}, Confidence: {dynamic['confidence']}%) - {dynamic['date'][:10]}" for dynamic in person_library['relationship_dynamics'][-3:]]) if person_library['relationship_dynamics'] else "No relationship dynamics analyzed yet"}

**LATEST ANALYSIS (Current Conversation):**
{f"Overall Pattern: {latest_analysis.get('overallPattern', 'Still analyzing...')}\nRisk Level: {latest_analysis.get('riskLevel', 'Unknown')}\nConfidence: {latest_analysis.get('confidence', 0)}%\nPrediction: {latest_analysis.get('prediction', 'Still gathering data...')}" if latest_analysis else "No analysis data for this conversation yet"}

**CONVERSATION HISTORY:**
{conversation_text if conversation_text else "No previous messages"}

Remember: You are analyzing {person_name} patterns and helping the user understand their relationship dynamics. Do not tell them what to feel or do - help them see patterns and ask thoughtful questions."""

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
                request.user.use_credit()

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
                        "person_library_size": sum(len(v) for v in person_library.values()),
                        "has_latest_analysis": bool(latest_analysis),
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