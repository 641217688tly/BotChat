from chat.models import Topic, Conversation
from user.serializers import UserSerializer
from rest_framework import serializers
import base64

class TopicSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    topic_id = serializers.IntegerField(source='id')  # 使用source属性指向模型的id字段
    class Meta:
        model = Topic
        fields = ['topic_id', 'user', 'theme', 'context', 'custom_context']

class ConversationSerializer(serializers.ModelSerializer):
    # topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.all()) # 只显示topic的主键
    topic = TopicSerializer(read_only=True)
    conversation_id = serializers.IntegerField(source='id')  # 使用source属性指向模型的id字段
    prompt_word = serializers.CharField(source='prompt')  # 将原prompt字段映射为新的prompt_word字段
    response_word = serializers.CharField(source='response')  # 将原response字段映射为新的response_word字段
    prompt_voice = serializers.SerializerMethodField()  # 更改后的字段名
    response_voice = serializers.SerializerMethodField()  # 更改后的字段名

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'topic', 'prompt_word', 'response_word', 'prompt_voice', 'response_voice', 'audio_assessment']  # 更改字段名
    def get_prompt_voice(self, obj):  # 更改后的获取方法
        if obj.prompt_audio:
            return base64.b64encode(obj.prompt_audio).decode('utf-8')
        return None
    def get_response_voice(self, obj):  # 更改后的获取方法
        if obj.response_audio:
            return base64.b64encode(obj.response_audio).decode('utf-8')
        return None
