from rest_framework import serializers
from .models import CustomUser, Conversation, Message, FavoriteConversation, Provider, ServiceOffering

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'input_type',
            'text_content',
            'image',
            'builder_data',
            'type',
            'analysis_data',
            'created_at'
        ]

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'uuid', 'title', 'created_at', 'updated_at', 'messages', 'is_favorite']
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


class FavoriteConversationSerializer(serializers.ModelSerializer):
    conversation = ConversationSerializer(read_only=True)
    
    class Meta:
        model = FavoriteConversation
        fields = ['id', 'conversation', 'created_at']
        read_only_fields = ['created_at']

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = '__all__'  # or make sure 'availability' is in the explicit list
        read_only_fields = ['user']

class ServiceOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffering
        fields = ['id', 'provider', 'service_type', 'service_title', 'description', 'offerings', 'pricing', 'availability', 'travel_option', 'venue_address', 'created_at']
        read_only_fields = ['provider', 'created_at']