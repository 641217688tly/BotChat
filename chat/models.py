from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Record(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')  # 级联删除,当用户被删除时,其所有记录也会被删除
    theme = models.CharField(max_length=30, default='new chat')
    question = models.TextField(blank=True)  # 应该足够长
    answer = models.TextField(blank=True)  # 应该足够长,且允许为空,以避免有时因服务器错误导致的回答失败
    created_time = models.DateTimeField(auto_now_add=True)  # 只在对象首次创建时设置
    context = models.TextField(blank=True, default='')  # 记录该行之前对话记录的语境，允许为空，并且默认值为空

    class Meta:
        db_table = 'records'

    def __str__(self):
        return f'User: {self.user}; Created Time: {self.created_time}'


# Topic模型
class Topic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')  # 级联删除: 当用户被删除时，其所有话题也会被删除
    theme = models.CharField(max_length=30, default='new chat')
    context = models.TextField(blank=True, default='')  # 记录该话题的上下文，允许为空，并且默认值为空
    class Meta:
        db_table = 'topics'
    def __str__(self):
        return f'User: {self.user}; Theme: {self.theme}'


# Conversation模型
class Conversation(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='conversations')  # 级联删除: 当话题被删除时，其所有对话也会被删除
    created_time = models.DateTimeField(auto_now_add=True)  # 只在对象首次创建时设置
    prompt = models.TextField(blank=True)  # 用户的提问
    response = models.TextField(blank=True)  # bot的回复
    class Meta:
        db_table = 'conversations'
        ordering = ['created_time']  # 按创建时间排序
    def __str__(self):
        return f'Topic: {self.topic}; Created Time: {self.created_time}'
