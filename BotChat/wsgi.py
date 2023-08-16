"""
WSGI config for BotChat project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from chat.utils import load_whisper_model
from chat.utils import load_config_constant

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BotChat.settings")

application = get_wsgi_application()

load_whisper_model() # 在服务器启动时加载faster-whisper模型

load_config_constant() # 在服务器启动时加载配置文件