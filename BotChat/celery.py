from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置 Django 的 settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BotChat.settings')

app = Celery('BotChat')

# 从 Django 的设置模块中导入 CELERY 配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有注册的 Django app 中的任务
app.autodiscover_tasks(['chat.utils'])

