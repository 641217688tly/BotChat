from django.urls import path
from user.views import *

urlpatterns = [
    path('register/', register),  # 完整url: /botchat/user/register/
    path('login/', login),  # 完整url: /botchat/user/login/
    path('change/info/', change_user_info),  # 完整url: /botchat/user/change/info/
]
