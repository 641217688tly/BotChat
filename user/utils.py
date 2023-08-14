import jwt
import yaml
from django.contrib.auth.models import User
from datetime import datetime, timedelta

# 加载YAML配置文件
with open('config.yml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)
# 从配置中获取JWT密钥
JWT_SECRET_KEY = config['JWT_SECRET_KEY']


def generate_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=14)  # token有效期设置为14天
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    return token  # 直接返回token字符串，不再执行解码


def judge_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        user = User.objects.get(id=user_id)
        # 验证用户是否存在
        if user is None:
            return False
        # 如果要进一步验证其他内容，可以在此处添加
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False
    except User.DoesNotExist:
        return False


def obtain_user(token):
    if judge_token(token):
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        user_id = payload['user_id']
        user = User.objects.get(id=user_id)
        return user
    return None
