import json

from django.utils import timezone
from django.shortcuts import render
from chat.utils import *
from user.utils import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chat.models import *


@csrf_exempt
def homepage(request):
    """
       期望的接收值:
       - 无特定参数，只接收一个常规的HTTP请求。可能包括一个有效的'X-Requested-With' header，表示一个AJAX请求。
       功能介绍:
       - 如果是一个AJAX请求并且用户通过token验证, 会获取该用户所有的话题并返回。
       - 如果不是AJAX请求，则渲染一个页面给前端。
       返回值:
       - 如果是AJAX请求: 返回一个包含用户所有话题(topics)的JSON响应。
       - 否则: 返回一个渲染好的页面。
       """
    print("homepage() method is running...")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        print("homepage() method is handling AJAX request...")
        token = request.COOKIES.get('token', None)
        user = obtain_user(token) if token else None
        topic_list = []
        if user:
            topics = Topic.objects.filter(user=user)
            for topic in topics:
                topic_data = {
                    'id': topic.id,
                    'theme': topic.theme,
                }
                topic_list.append(topic_data)
        print("homepage() method is handling AJAX request and return JsonResponse({'topics': topic_list})")
        return JsonResponse({'topics': topic_list})
    print("homepage() return render(request, 'chat/botchat.html')")
    return render(request, 'chat/botchat.html')


@csrf_exempt
def create_chat(request):
    """
    期望的接收值:
    - 无特定参数，仅从cookie中获取token以校验和获取User对象。
    功能介绍:
    - 根据token确定用户身份并为其创建新的话题。
    返回值:
    - 成功: 返回新创建话题的相关数据的JSON响应。
    - 失败: 返回一个表示错误的JSON响应。
    """
    token = request.COOKIES.get('token')  # 获取cookie中的token
    user = obtain_user(token)
    if not user:
        return JsonResponse({'error': 'Invalid token or user not found.'}, status=401)
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    theme_name = f"{user.username}:{current_time}"
    new_topic = Topic.objects.create(user=user, theme=theme_name)
    new_topic.save()
    topic_data = {
        'id': new_topic.id,
        'theme': new_topic.theme,
    }
    return JsonResponse({'topic': topic_data})


@csrf_exempt
def change_topic(request):
    """
    期望的接收值:
    - POST请求。
    - 从cookie中获取token。
    - POST data应该包含一个'topic_id'字段。
    功能介绍:
    - 切换到给定的话题并为前端提供与该话题相关的所有对话记录。
    返回值:
    - 成功: 返回一个包含所有相关对话记录的JSON响应。
    - 失败: 返回一个表示错误的JSON响应。
    """
    if request.method == 'POST':
        token = request.COOKIES.get('token', None)
        # 通过 token 获取用户对象
        user = obtain_user(token)
        if user is None:
            return JsonResponse({'status': 'invalid token'}, status=400)
        # 获取topic的id
        topic_id = request.POST.get('topic_id', None)
        if topic_id is None:
            return JsonResponse({'status': 'topic_id not provided'}, status=400)
        request.session['topic_id'] = topic_id  # 更新或创建session中的topic_id
        # 获取与主题相关的Topic对象
        try:
            selected_topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return JsonResponse({'status': 'topic does not exist'}, status=400)
        # 获取与该主题相关的Conversation对象
        conversations = Conversation.objects.filter(topic=selected_topic).order_by('created_time')
        conversation_list = []
        for conversation in conversations:
            conversation_list.append({
                'user': user.username,
                'text': conversation.prompt,
                'bot_reply': conversation.response,
                'timestamp': conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
            })
        return JsonResponse({'records': conversation_list})
    return JsonResponse({'status': 'invalid request method'}, status=400)


@csrf_exempt
def receive_text(request):
    """
    期望的接收值:
    - POST请求。
    - JSON格式的请求体，包含一个"text"字段。
    功能介绍:
    - 获取用户提供的文本并保存为一个对话(Conversation)。如果用户没有选择话题(即Session中没有topic_id)，则为其创建一个新话题(Topic)。
    返回值:
    - 成功: 返回相关的对话和话题数据。
    - 失败: 返回一个表示错误的JSON响应。
    """
    if request.method == "POST":
        token = request.COOKIES.get('token')
        user = obtain_user(token)
        if user is None:
            return JsonResponse({'error': 'Invalid user'}, status=400)
        data = json.loads(request.body.decode('utf-8'))
        user_text = data.get('text')
        topic_id = request.session.get('topic_id')
        # 如果用户已选择主题
        if topic_id:
            try:
                topic = Topic.objects.get(id=topic_id)
            except Topic.DoesNotExist:
                return JsonResponse({'error': 'Topic does not exist'}, status=400)
            conversation = Conversation(topic=topic, prompt=user_text, response="")
            conversation.save()
            return JsonResponse({
                'type': 'existing_topic',
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response
                }
            })
        # 如果用户未选择主题
        else:
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            theme_name = f"{user.username}:{current_time}"
            new_topic = Topic.objects.create(user=user, theme=theme_name)
            conversation = Conversation(topic=new_topic, prompt=user_text, response="")
            conversation.save()
            # 存储新的topic_id到session中
            request.session['topic_id'] = new_topic.id
            topic_data = {
                'id': new_topic.id,
                'theme': new_topic.theme,
            }
            return JsonResponse({
                'type': 'new_topic',
                'topic': topic_data,
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response
                }
            })
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def receive_audio(request):
    """
    期望的接收值:
    - POST请求。
    - 包含音频文件。
    功能介绍:
    - 将音频文件转换为文本并保存为一个对话(Conversation)。如需要，会为用户创建新话题(Topic)。
    返回值:
    - 成功: 返回转换后的文本以及相关话题数据的JSON响应。
    - 失败: 返回一个表示错误的JSON响应。
    """
    print("receive_audio is running...")
    if request.method == "POST":
        token = request.COOKIES.get('token')
        user = obtain_user(token)
        if user is None:  # 检查从token中获取的用户对象是否存在
            return JsonResponse({'error': 'Invalid user'}, status=400)

        topic_id = request.session.get('topic_id')  # 从session中获取topic_id
        if topic_id:  # Session中存在topic_id,说明用户已经选择了主题
            topic = Topic.objects.filter(id=topic_id).first()
            if not topic:  # 如果通过ID找不到主题对象，则返回错误
                return JsonResponse({'error': 'Topic not found'}, status=400)
            # 进行音频处理
            audio_file = request.FILES['audio']
            converted_audio_file = convert_audio_format(audio_file) # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
            transcribed_text = audio_to_text(converted_audio_file) # 将音频转换为文本
            conversation = Conversation(topic=topic, prompt=transcribed_text)
            conversation.save()
            # asynchronously_save_audio_to_db.delay(conversation.id, converted_audio_file) #TODO 利用Celery实现异步存储音频文件,由于Docker尚未成功配置,因此暂时不使用Celery
            asynchronously_save_audio_to_db(conversation.id, converted_audio_file)
            response_data = {
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response,
                    'created_time': conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'type': 'existing_topic'
            }
        else:  # Session中不存在topic_id,说明用户还未选择主题,此时需要帮用户创建新的主题
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            theme_name = f"{user.username}:{current_time}"
            topic = Topic.objects.create(user=user, theme=theme_name)
            topic.save()
            request.session['topic_id'] = topic.id
            # 进行音频处理
            audio_file = request.FILES['audio']
            converted_audio_file = convert_audio_format(audio_file) # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
            transcribed_text = audio_to_text(converted_audio_file) # 将音频转换为文本
            conversation = Conversation(topic=topic, prompt=transcribed_text)
            conversation.save()
            # asynchronously_save_audio_to_db.delay(conversation.id, converted_audio_file) #TODO 利用Celery实现异步存储音频文件,由于Docker尚未成功配置,因此暂时不使用Celery
            asynchronously_save_audio_to_db(conversation.id, converted_audio_file)
            response_data = {
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response,
                    'created_time': conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'topic': {
                    'id': topic.id,
                    'theme': topic.theme,
                },
                'type': 'new_topic'
            }
        return JsonResponse(response_data)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def chat_with_openai(request):
    """
    期望的接收值:
    - POST请求。
    - JSON格式的请求体，包含一个"text"字段表示用户的提示。
    功能介绍:
    - 使用提供的提示与OpenAI聊天，并保存OpenAI的响应为一个对话。
    返回值:
    - 成功: 返回OpenAI的响应的JSON格式。
    - 失败: 返回一个表示错误的JSON响应。
    """
    if request.method == 'POST':
        # 从前端获取prompt
        prompt = json.loads(request.body.decode('utf-8'))['text']
        # 获取当前的topic_id
        topic_id = request.session.get('topic_id')
        # 1.获取历史聊天语境
        message = obtain_context(topic_id)
        # 2.将prompt与context结合以创建新的message
        message.append({"role": "user", "content": prompt})
        # 3.向openai发送请求并得到响应
        response = obtain_openai_response(message)
        # 4.将响应结果保存到数据库中
        latest_conversation = Conversation.objects.filter(topic_id=topic_id).order_by('-created_time').first()
        latest_conversation.response = response
        latest_conversation.save()
        # TODO 5.如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现
        asynchronously_update_context(topic_id, message, latest_conversation)
        # 6.将响应结果返回给前端(如果有可能,将响应结果转为语音后同步发送给前端)
        response_data = {
            'id': latest_conversation.id,
            'prompt': latest_conversation.prompt,
            'response': latest_conversation.response,
            'created_time': latest_conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        return JsonResponse({'conversation': response_data})
    return JsonResponse({'error': 'Invalid request'}, status=400)


# @csrf_exempt
# def receive_audio(request):
#     """
#     期望的接收值:
#     - POST请求。
#     - 包含音频文件。
#     功能介绍:
#     - 将音频文件转换为文本并保存为一个对话(Conversation)。如需要，会为用户创建新话题(Topic)。
#     返回值:
#     - 成功: 返回转换后的文本以及相关话题数据的JSON响应。
#     - 失败: 返回一个表示错误的JSON响应。
#     """
#     print("receive_audio is running...")
#     if request.method == "POST":
#         token = request.COOKIES.get('token')
#         user = obtain_user(token)
#         if user is None:  # 检查从token中获取的用户对象是否存在
#             return JsonResponse({'error': 'Invalid user'}, status=400)
#
#         topic_id = request.session.get('topic_id')  # 从session中获取topic_id
#         if topic_id:  # Session中存在topic_id,说明用户已经选择了主题
#             topic = Topic.objects.filter(id=topic_id).first()
#             if not topic:  # 如果通过ID找不到主题对象，则返回错误
#                 return JsonResponse({'error': 'Topic not found'}, status=400)
#             # 进行音频处理
#             audio_file = request.FILES['audio']
#             converted_audio_file = convert_audio_format(audio_file) # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
#
#             #TODO 在utils.py中自定义函数,将(音频文件转换为文本)和(存储音频文件进数据库)这两个步骤封装起来
#             with tempfile.TemporaryDirectory() as temp_dir:
#                 temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
#                 with open(temp_audio_path, 'wb') as temp_file:
#                     shutil.copyfileobj(converted_audio_file, temp_file)
#                 transcribed_text = transcribe_audio(temp_audio_path)
#                 conversation = Conversation(topic=topic, prompt=transcribed_text)
#                 conversation.save()
#             response_data = {
#                 'conversation': {
#                     'id': conversation.id,
#                     'prompt': conversation.prompt,
#                     'response': conversation.response,
#                     'created_time': conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
#                 },
#                 'type': 'existing_topic'
#             }
#         else:  # Session中不存在topic_id,说明用户还未选择主题,此时需要帮用户创建新的主题
#             current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#             theme_name = f"{user.username}:{current_time}"
#             topic = Topic.objects.create(user=user, theme=theme_name)
#             topic.save()
#             request.session['topic_id'] = topic.id
#             # 进行音频处理
#             audio_file = request.FILES['audio']
#             converted_audio_file = convert_audio_format(audio_file) # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
#             # TODO 在utils.py中自定义函数,将(音频文件转换为文本)和(存储音频文件进数据库)这两个步骤封装起来
#             with tempfile.TemporaryDirectory() as temp_dir:
#                 temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
#                 with open(temp_audio_path, 'wb') as temp_file:
#                     shutil.copyfileobj(converted_audio_file, temp_file)
#                 transcribed_text = transcribe_audio(temp_audio_path)
#                 conversation = Conversation(topic=topic, prompt=transcribed_text)
#                 conversation.save()
#             response_data = {
#                 'conversation': {
#                     'id': conversation.id,
#                     'prompt': conversation.prompt,
#                     'response': conversation.response,
#                     'created_time': conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
#                 },
#                 'topic': {
#                     'id': topic.id,
#                     'theme': topic.theme,
#                 },
#                 'type': 'new_topic'
#             }
#         return JsonResponse(response_data)
#     return JsonResponse({'error': 'Invalid request'}, status=400)


