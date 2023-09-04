"""
Django settings for BotChat project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-j6hs!9g(qs%74-b41$)%%^)chn0i5hd#36srp$6bwheovh_a!h"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]  # TODO 在测试时使用，允许所有的主机访问;在部署上线前,应该更改为允许访问的主机的IP地址和域名(即我的云服务器的ip地址和我购买的域名)

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'corsheaders',
    'rest_framework',  # 添加rest_framework
    'user',
    'chat',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    'corsheaders.middleware.CorsMiddleware',# 添加corsheaders中间件以处理跨域请求
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "user.middleware.UserAuthenticationMiddleware",  # 由于不打算使用JWT来实现用户认证，所以注释掉该中间件
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "BotChat.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # 由于不打算使用模板，所以应该可以注释掉: BASE_DIR / 'templates'
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "BotChat.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases


# 在使用Docker来管理项目的各个容器时使用以下配置:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'botchat',
#         'USER': 'root',
#         'PASSWORD': '20030207TLY',
#         'HOST': 'db',  # 这里更改为'db'
#         'PORT': 3306,
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'botchat',
        'USER': 'root',
        'PASSWORD': '20030207TLY',
        'HOST': 'localhost',
        'PORT': 3306,
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "zh-hans"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [  # 静态文件目录,用于指定非static文件夹下的静态文件的位置
    BASE_DIR / 'static',
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 配置Django日志
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {  # 只针对请求日志
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# 使用Docker管理项目容器时采用如下配置方法来配置celery:
# CELERY_BROKER_URL = 'redis://redis:6379/0' # 使用本地的 Redis
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0' # 使用 Redis 存储结果


# 不使用Docker管理项目容器时采用如下配置方法来配置celery:
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # 使用本地的 Redis
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # 使用 Redis 存储结果


# DRF配置:
REST_FRAMEWORK = {
    'PAGE_SIZE': 25,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer'  # 为了方便开发和调试，保留了BrowsableAPIRenderer
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',  # 因为要处理音频文件上传
        'rest_framework.parsers.FormParser'  # 可处理表单数据
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # 默认权限，意味着只有经过身份验证的用户才可以访问API视图
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',  # 基本的HTTP认证，通常在开发环境中使用
        'rest_framework.authentication.SessionAuthentication',  # Django的session认证，如果您使用Django的登录系统也可以保留
        'rest_framework.authentication.TokenAuthentication',  # Token身份验证
    ],
}

DEFAULT_TOPIC_CONTEXT = "chatGPT Role: You are an oral English teacher fluent in both Chinese and English. The following system content is the former conversation between user and you. Please answer the user's questions in a manner that mimics that of an oral English teacher. Unless specifically requested by the user, the length of each answer should be limited to 125 words."

AUDIO_ASSESSMENT_REQUIREMENT_PROMPT = "上述xml格式的文本是对用户一段英语发音的评分.请根据上述xml文本提供的评分细节,总结用户的得分情况和最终成绩并使用流畅的简体中文输出结果.绝大部分的评分标准不需要给出具体分数,只需要根据分数高低大概地笼统地评价.请注意:所有评分标准都是以0分作为最低分,以5分作为最高分,值为负数的参数请忽略不计.你的回答需要严肃、客观,对于用户得分较高的部分可以加以赞赏,对于用户得分较低的部分可以指出可能存在的问题.以上xml文本中的评分标准不需要向用户解释"

# 配置CORS:
CORS_ALLOW_ALL_ORIGINS = True
