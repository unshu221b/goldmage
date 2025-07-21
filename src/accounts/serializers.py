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
            'type',
            'search_results',
            'total_amount',
            'currency',
            'payment_status',
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
        fields = ['id', 'provider', 'service_title', 'description', 'offerings', 'pricing', 'travel_option', 'venue_address', 'created_at', 'thumbnail_url']
        read_only_fields = ['provider', 'created_at']

class ServiceOfferingSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffering
        fields = ['id', 'service_title', 'description', 'thumbnail_url']

class ProviderWithOfferingsSerializer(serializers.ModelSerializer):
    offerings = ServiceOfferingSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Provider
        fields = [
            'id', 'name', 'bio', 'icon_url', 'is_promoted', 'completion_count',
            'offerings'
        ]