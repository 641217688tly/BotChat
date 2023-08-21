import os
from celery import Celery
from django.conf import settings

# 设置 'chat' 的 Django 设置模块为 Celery 的默认设置。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BotChat.settings')

app = Celery('chat')

# 从 Django 的设置文件中加载 Celery 的配置。
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动加载在所有已注册的 Django app configs 中名为 'tasks.py' 的任何模块。
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
