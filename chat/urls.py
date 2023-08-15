from django.urls import path
from chat.views import *

urlpatterns = [
    path('homepage/', homepage), # 完整url: /chat/homepage/
    path('create_chat/', create_chat), # 完整url: /chat/create_chat/
    path('change_topic/', change_topic), # 完整url: /chat/change_topic/
    path('receive_text/', receive_text), # 完整url: /chat/receive_text/
    path('receive_audio/', receive_audio), # 完整url: /chat/receive_audio/
    path('chat_with_openai/', chat_with_openai), # 完整url: /chat/chat_with_openai/

]
