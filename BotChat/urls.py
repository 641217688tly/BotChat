from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path('botchat/chat/', include('chat.urls')),  # 添加chat应用的路径
    path('botchat/user/', include('user.urls')),  # 添加user应用的路径
    # path('', RedirectView.as_view(url='botchat/user/login/', permanent=False)),  # 这里将根URL重定向到登录页面
]
