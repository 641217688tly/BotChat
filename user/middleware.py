from user.utils import judge_token
from django.http import HttpResponseRedirect


class UserAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed_paths = ['/user/login/', '/user/register/']
        if not any(request.path.startswith(path) for path in allowed_paths) and not request.path.startswith('/admin/'):
            token = request.COOKIES.get('token', None)  # 从cookie中获取token
            if not token or not judge_token(token):
                return HttpResponseRedirect('/user/login/')  # 重定向到登录页面的视图函数URL

        response = self.get_response(request)
        return response