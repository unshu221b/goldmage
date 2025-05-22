from rest_framework import serializers
from .models import CustomUser, Conversation, Message, MessageAnalysis

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True}
        }

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

class MessageAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAnalysis
        fields = '__all__' 

class MessageRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    sender = serializers.CharField()

class AnalysisRequestSerializer(serializers.Serializer):
    messages = serializers.ListField(
        child=MessageRequestSerializer()
    )

class SuggestionSerializer(serializers.Serializer):
    id = serializers.CharField()
    suggestion = serializers.CharField()
    style = serializers.CharField()

class PersonalityMetricsSerializer(serializers.Serializer):
    intelligence = serializers.IntegerField(allow_null=True)
    charisma = serializers.IntegerField(allow_null=True)
    strength = serializers.IntegerField(allow_null=True)
    kindness = serializers.IntegerField(allow_null=True)

class EmotionMetricsSerializer(serializers.Serializer):
    happiness = serializers.IntegerField()
    sadness = serializers.IntegerField()
    anger = serializers.IntegerField()
    surprise = serializers.IntegerField()
    fear = serializers.IntegerField()
    disgust = serializers.IntegerField()
    neutral = serializers.IntegerField()

class AnalysisResponseSerializer(serializers.Serializer):
    reaction = serializers.CharField()
    suggestions = SuggestionSerializer(many=True)
    personality_metrics = PersonalityMetricsSerializer()
    emotion_metrics = EmotionMetricsSerializer()