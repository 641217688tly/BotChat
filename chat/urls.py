from django.urls import path
from chat.views import *

urlpatterns = [
    path('gettopics/', get_topics),
    path('getdetails/', get_topic_details),
    path('sendvoice/', receive_audio),
    path('sendword/', receive_text),
    path('newtopic/',  create_topic),
    path('change/theme/', receive_text),

]
