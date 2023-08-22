from django.urls import path
from chat.views import *

urlpatterns = [
    path('gettopics/', get_topics),
    path('getdetails/', get_topic_details),
    path('sendvoice/', send_voice),
    path('sendword/', send_word),
    path('newtopic/',  create_topic),
    path('change/theme/', send_word),


    # path('create_chat/', create_chat), # 完整url: /botchat/chat/create_chat/
    # path('change_topic/', change_topic), # 完整url: /botchat/chat/change_topic/
    # path('receive_text/', receive_text), # 完整url: /botchat/chat/receive_text/
    # path('receive_audio/', receive_audio), # 完整url: /botchat/chat/receive_audio/
    # path('chat_with_openai/', chat_with_openai), # 完整url: /botchat/chat/chat_with_openai/

]
