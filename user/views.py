import json
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from user.utils import *
from django.shortcuts import redirect

@csrf_exempt
def login(request):
    """用户登录视图。
    该视图功能包括：
    - GET请求：展示登录页面。
    - POST请求：验证用户提供的用户名和密码，并生成对应的token。
    如果用户名和密码验证成功，视图将返回带有token的JSON响应，同时将token作为cookie存储。
    如果验证失败，返回错误信息。
    Args:
    - request (HttpRequest): Django请求对象。
    Returns:
    - HttpResponse: 根据情况返回的反馈消息。
    """
    print("login method is running...")
    # 检查cookie中是否有token
    # token = request.COOKIES.get('token')
    # if token and judge_token(token):
    #     # token有效，重定向用户到/chat/homepage/
    #     return redirect('/chat/homepage/')
    if request.method == 'GET':
        return render(request, 'user/login.html')
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        username = data['username']
        password = data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            token = generate_token(user)
            response_data = {'status': 20041, 'data': {'token': token}, 'msg': 'Login successful'}
            response = JsonResponse(response_data)
            # 设置cookie，并设置有效期为2周
            max_age = 14 * 24 * 60 * 60
            response.set_cookie('token', token, max_age=max_age, httponly=True)
            return response
        else:
            response_data = {'status': 40041, 'msg': 'Invalid username or password'}
            return JsonResponse(response_data)
    return JsonResponse({'status': 405, 'msg': 'Method not allowed'}, status=405)


@csrf_exempt
def register(request):
    """用户注册视图。
    该视图功能包括：
    - GET请求：展示注册页面。
    - POST请求：基于用户提供的数据创建新的用户账号。
    在用户提交注册数据时，视图会检查用户名或电子邮件是否已存在。
    如果验证通过，新的用户会被创建并保存。
    Args:
    - request (HttpRequest): Django请求对象。
    Returns:
    - HttpResponse: 根据情况返回的反馈响应。
    """
    print("register method is running...")
    if request.method == 'GET':
        return render(request, 'user/register.html')
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8')) # 解析JSON数据
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return JsonResponse({'status': 40011, 'msg': 'Username already exists'})
        # 检查电子邮件是否已存在
        if User.objects.filter(email=email).exists():
            return JsonResponse({'status': 40012, 'msg': 'Email already exists'})
        # 创建并保存用户
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        print("register method is running...user is saved")
        return JsonResponse({'status': 20011, 'msg': 'Registration successful'})
    return JsonResponse({'status': 400, 'msg': 'Bad Request'}, status=400)

