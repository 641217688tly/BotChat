from rest_framework.response import Response
from user.serializers import UserSerializer
from user.utils import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import make_password, check_password


@api_view(['POST'])
@permission_classes([])
def login(request): # localhost/botchat/user/login
    """
    用户登录视图。
    该视图接受POST请求，根据用户提供的用户名和密码进行验证。
    如果用户名和密码匹配：
    - 返回用户信息的JSON响应。
    如果验证失败：
    - 返回错误信息。
    Args:
    - request (HttpRequest): 包含'username'和'password'键值对的请求对象。
    Returns:
    - Response:
        * 若验证成功，返回用户信息并设置状态码为200。
        * 若密码不正确，返回错误信息并设置状态码为401。
        * 若用户不存在，返回错误信息并设置状态码为404。
    """
    try:
        user = User.objects.get(username=request.data['username'])
        if check_password(request.data['password'],
                          user.password):  # 采用rest_framework自带的check_password函数来将前端传入的用户密码进行加密后与数据库中的密码进行比对
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'message': 'Incorrect password.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'User does not exist.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([])
def register(request): # localhost/botchat/user/register
    """
    用户注册视图。
    该视图接受POST请求，基于用户提供的数据创建新的用户账号。
    在用户提交注册数据时：
    - 视图会检查用户名是否已存在。
    - 如果用户名唯一且数据有效，新的用户会被创建并保存，密码会进行加密处理。
    Args:
    - request (HttpRequest): 包含'username', 'password'和'email'键值对的请求对象。
    Returns:
    - Response:
        * 若创建成功，返回新用户信息并设置状态码为201。
        * 若用户名已存在，返回错误信息并设置状态码为400。
        * 若数据无效或有其他问题，返回错误信息并设置状态码为400。
    """
    user_serializer = UserSerializer(data=request.data)
    if user_serializer.is_valid():
        # 检查用户名是否已存在
        if User.objects.filter(username=user_serializer.validated_data['username']).exists():
            return Response({
                'status': 'error',
                'message': 'Username already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        # 手动加密密码
        user_serializer.validated_data['password'] = make_password(
            user_serializer.validated_data['password'])  # 将用户的密码进行单向加密后再存入数据库
        user = user_serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def change_user_info(request): # localhost/botchat/user/change/info/
    user_id = int(request.data.get('user_id'))
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    print(username, email, password)
    try:
        # 获取对应的用户对象并更新信息
        user = User.objects.get(id=user_id)
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if password is not None:
            user.password = make_password(password)  # 使用Django的make_password方法对密码进行哈希处理
        user.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        return Response({'error': 'User does not exist'}, status=404)
