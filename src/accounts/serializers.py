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