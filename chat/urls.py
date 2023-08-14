from django.urls import path
from chat.views import *

urlpatterns = [
    path('homepage/', homepage),
    path('create_chat/', create_chat),
    path('change_theme/', change_theme),
    path('receive_text/', receive_text),
    path('receive_audio/', receive_audio),
    path('chat_with_openai/', chat_with_openai),

]
