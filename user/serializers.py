from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()  # 新增的字段
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'password']
    def get_user_id(self, obj):
        return obj.id