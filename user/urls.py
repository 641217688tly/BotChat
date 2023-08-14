from django.urls import path
from user.views import *

urlpatterns = [
    path('register/',register),
    path('login/',login),

]
