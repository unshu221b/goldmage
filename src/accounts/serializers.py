from rest_framework import serializers
from .models import CustomUser, Conversation, Message, MessageAnalysis, ConversationAnalysis, FavoriteConversation

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'
    
# For the nested data structures
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

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'sender', 'input_type', 'text_content', 'image', 'builder_data', 'created_at']

# The main ConversationAnalysis serializer
class ConversationAnalysisSerializer(serializers.ModelSerializer):
    # Remove old fields/serializers and add new ones
    emotions = serializers.ListField()
    patterns = serializers.ListField()
    risks = serializers.ListField()
    communication = serializers.ListField()
    overallPattern = serializers.CharField()
    riskLevel = serializers.CharField()
    confidence = serializers.IntegerField()
    prediction = serializers.CharField()

    class Meta:
        model = ConversationAnalysis
        fields = [
            'emotions',
            'patterns',
            'risks',
            'communication',
            'overallPattern',
            'riskLevel',
            'confidence',
            'prediction',
            'created_at',
            'updated_at'
        ]

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    analysis = ConversationAnalysisSerializer(read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'uuid', 'title', 'created_at', 'updated_at', 'messages', 'analysis', 'is_favorite']
        extra_kwargs = {
            'user': {'read_only': True},
            'uuid': {'read_only': True}
        }
    
    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FavoriteConversation.objects.filter(
                user=request.user,
                conversation=obj
            ).exists()
        return False

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

class FavoriteConversationSerializer(serializers.ModelSerializer):
    conversation = ConversationSerializer(read_only=True)
    
    class Meta:
        model = FavoriteConversation
        fields = ['id', 'conversation', 'created_at']
        read_only_fields = ['created_at']