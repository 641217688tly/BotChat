from __future__ import absolute_import, unicode_literals

# 这将确保应用程序始终在 Django 启动时导入。
from BotChat.celery import app as celery_app

__all__ = ('celery_app',)
