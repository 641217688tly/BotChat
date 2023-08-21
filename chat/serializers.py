from rest_framework import serializers
from .models import Topic, Conversation
from user.serializers import UserSerializer

class TopicSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # 只读，展示简化的用户信息
    class Meta:
        model = Topic
        fields = ['id', 'user', 'theme', 'context']

class ConversationSerializer(serializers.ModelSerializer):
    topic = TopicSerializer(read_only=True)  # 只读，展示话题的详细信息
    class Meta:
        model = Conversation
        fields = ['id', 'topic', 'created_time', 'prompt', 'response', 'prompt_audio', 'response_audio']
