from django.core.files.base import ContentFile
from django.utils import timezone
from chat.utils import *
from user.utils import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chat.serializers import *
from chat.models import *
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_topics(request):  # localhost/botchat/chat/gettopics/?user_id
    user_id = request.GET.get('user_id')
    if user_id is None:
        return Response({"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    # 获取用户相关的topic
    topics = Topic.objects.filter(user__id=user_id)  # 通过外键user__id跨关系查询与该用户相关的topic
    # 序列化这些topic
    serializer = TopicSerializer(topics, many=True)
    return Response({"topics": serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_topic_details(request):  # localhost/botchat/chat/getdetails/?topic_id
    # 获取GET参数中的topic_id
    topic_id = request.GET.get('topic_id')
    if not topic_id:
        return Response({'error': 'Missing topic_id parameter'}, status=400)
    # 查询对应的Conversations
    conversations = Conversation.objects.filter(topic__id=topic_id)
    # 序列化数据
    serializer = ConversationSerializer(conversations, many=True)
    serialized_data = serializer.data
    # 构造新的JSON结构以符合前端的需求
    details = []
    for item in serialized_data:
        detail = {
            'detail_id': item['conversation_id'],
            'prompt': item['prompt_word'],
            'response_word': item['response_word'],
            'response_voice': item['response_voice']
        }
        details.append(detail)
    return Response({'details': details})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_text(request):  # localhost/botchat/chat/sendword/
    user_id = request.data.get('user_id')
    prompt = request.data.get('prompt_word')
    topic_id = request.data.get('topic_id')
    # 确保数据完整性
    if (user_id and prompt and topic_id) is None:
        return Response({'error': 'Missing required data!'}, status=400)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=400)
    if topic_id == '-1':  # 创建新的Topic
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        theme_name = f"{user.username}:{current_time}"
        topic = Topic.objects.create(user=user, theme=theme_name)
        topic_id = topic.id  # 更新topic_id为新创建的Topic的id
    else:
        topic = Topic.objects.filter(id=topic_id).first()
        if topic is None:
            return Response({'error': 'Invalid topic'}, status=400)

    message = obtain_context(topic_id)  # 获取历史聊天语境
    message.append({"role": "user", "content": prompt})  # 将prompt与context结合以创建新的message
    response = obtain_openai_response(message)  # 向openai发送请求并得到响应
    new_conversation = Conversation.objects.create(
        topic=topic,
        prompt=prompt,
        response=response,
        response_audio=b''
    )
    new_conversation.save()
    # TODO 语音合成时出现报错
    save_audio_from_xunfei(response, new_conversation)  # 生成并保存音频
    response_audio = convert_audio_to_base64(new_conversation.response_audio)  # 读取数据库中的音频并转成base64格式
    asynchronously_update_context(topic_id, message, new_conversation)  # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现)
    return Response({  # 返回响应
        'response_word': response,
        'response_voice': response_audio,
        'topic_id': topic_id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_audio(request):  # localhost/botchat/chat/sendvoice/
    # 从请求中获取user_id和prompt_voice
    user_id = request.data.get('user_id')
    prompt_audio = request.data.get('prompt_voice')
    topic_id = request.data.get('topic_id')

    if (user_id and prompt_audio and topic_id) is None:
        return Response({'error': 'Missing required data!'}, status=400)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=400)

    if topic_id == '-1':  # 创建新的Topic
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        theme_name = f"{user.username}:{current_time}"
        topic = Topic.objects.create(user=user, theme=theme_name)
        topic_id = topic.id  # 更新topic_id为新创建的Topic的id
    else:
        topic = Topic.objects.filter(id=topic_id).first()
        if topic is None:
            return Response({'error': 'Invalid topic'}, status=400)

    audio_file = ContentFile(prompt_audio.read())  # 处理语音，转换为文本
    converted_audio_file = convert_audio_format(audio_file)  # 如果需要，转换音频格式为合适的格式
    prompt = audio_to_text(converted_audio_file)  # 将音频转换为文本
    message = obtain_context(topic_id)  # 获取历史聊天语境
    message.append({"role": "user", "content": prompt})  # 将prompt与context结合以创建新的message
    response = obtain_openai_response(message)  # 向openai发送请求并得到响应
    new_conversation = Conversation.objects.create(
        topic=topic,
        prompt=prompt,
        response=response,
        prompt_audio=b'',
        response_audio=b''
    )
    new_conversation.prompt_audio = prompt_audio
    new_conversation.save()
    # TODO 语音合成时出现报错
    save_audio_from_xunfei(response, new_conversation)  # 生成并保存音频
    response_audio = convert_audio_to_base64(new_conversation.response_audio)  # 读取数据库中的音频并转成base64格式
    asynchronously_update_context(topic_id, message,
                                  new_conversation)  # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现)
    return Response({  # 返回响应
        'response_word': response,
        'response_voice': response_audio,
        'topic_id': topic_id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_theme(request): #  localhost/botchat/chat/change/theme/
    topic_id = request.data.get('topic_id')
    new_theme = request.data.get('theme')
    # 确保数据完整性
    if (topic_id and new_theme) is None:
        return Response({'error': 'Missing topic_id or theme data'}, status=400)
    try:
        # 获取对应的Topic对象并更新
        topic = Topic.objects.get(id=topic_id)
        topic.theme = new_theme
        topic.save()
        return Response({'message': 'Theme updated successfully'})
    except Topic.DoesNotExist:
        return Response({'error': 'Topic does not exist'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_topic(request):  # localhost/botchat/chat/newtopic/
    user_id = request.data.get('user_id')
    # 确保数据完整性
    if user_id is None:
        return Response({'error': 'user_id is required!'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
    # 创建新的Topic
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    theme_name = f"{user.username}:{current_time}"
    new_topic = Topic.objects.create(user=user, theme=theme_name)
    new_topic.save()
    # 获取与此用户相关的所有topics
    topics = Topic.objects.filter(user=user)
    serializer = TopicSerializer(topics, many=True)
    return Response({"topics": serializer.data})


# ------------------------------------将获取openai响应与合成语音的功能进行拆分------------------------------------
# ------------------------------------将获取openai响应与合成语音的功能进行拆分------------------------------------

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def receive_text(request):  # localhost/botchat/chat/sendword
#     user_id = request.data.get('user_id')
#     prompt = request.data.get('prompt_word')
#     topic_id = request.data.get('topic_id')
#     # 确保数据完整性
#     if (user_id and prompt and topic_id) is None:
#         return Response({'error': 'Missing required data!'}, status=400)
#     user = User.objects.filter(id=user_id).first()
#     if user is None:
#         return Response({'error': 'Invalid user'}, status=400)
#     if topic_id == '-1':  # 创建新的Topic
#         current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#         theme_name = f"{user.username}:{current_time}"
#         topic = Topic.objects.create(user=user, theme=theme_name)
#         topic_id = topic.id  # 更新topic_id为新创建的Topic的id
#     else:
#         topic = Topic.objects.filter(id=topic_id).first()
#         if topic is None:
#             return Response({'error': 'Invalid topic'}, status=400)
#
#     message = obtain_context(topic_id)  # 获取历史聊天语境
#     message.append({"role": "user", "content": prompt})  # 将prompt与context结合以创建新的message
#     response = obtain_openai_response(message)  # 向openai发送请求并得到响应
#     new_conversation = Conversation.objects.create(
#         topic=topic,
#         prompt=prompt,
#         response=response,
#     )
#     new_conversation.save()
#     asynchronously_update_context(topic_id, message,
#                                   new_conversation)  # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现)
#     return Response({  # 返回响应
#         'topic_id': topic_id,
#         'conversation_id': new_conversation.id,
#         'response_word': response
#     })
#
#
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def receive_audio(request):  # localhost/botchat/chat/sendvoice
#     # 从请求中获取user_id和prompt_voice
#     user_id = request.data.get('user_id')
#     prompt_audio = request.data.get('prompt_voice')
#     topic_id = request.data.get('topic_id')
#
#     if (user_id and prompt_audio and topic_id) is None:
#         return Response({'error': 'Missing required data!'}, status=400)
#     user = User.objects.filter(id=user_id).first()
#     if user is None:
#         return Response({'error': 'Invalid user'}, status=400)
#
#     if topic_id == '-1':  # 创建新的Topic
#         current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#         theme_name = f"{user.username}:{current_time}"
#         topic = Topic.objects.create(user=user, theme=theme_name)
#         topic_id = topic.id  # 更新topic_id为新创建的Topic的id
#     else:
#         topic = Topic.objects.filter(id=topic_id).first()
#         if topic is None:
#             return Response({'error': 'Invalid topic'}, status=400)
#
#     audio_file = ContentFile(prompt_audio.read())  # 处理语音，转换为文本
#     converted_audio_file = convert_audio_format(audio_file)  # 如果需要，转换音频格式为合适的格式
#     prompt = audio_to_text(converted_audio_file)  # 将音频转换为文本
#     message = obtain_context(topic_id)  # 获取历史聊天语境
#     message.append({"role": "user", "content": prompt})  # 将prompt与context结合以创建新的message
#     response = obtain_openai_response(message)  # 向openai发送请求并得到响应
#     # 创建一个以topic_id为外键的Conversation对象
#     new_conversation = Conversation.objects.create(
#         topic=topic,
#         prompt=prompt,
#         response=response,
#         prompt_audio=prompt_audio,
#     )
#     new_conversation.save()
#     asynchronously_update_context(topic_id, message,
#                                   new_conversation)  # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现)
#     return Response({  # 返回响应
#         'topic_id': topic_id,
#         'conversation_id': new_conversation.id,
#         'response_word': response
#     })
#
#
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def send_audio(request):  # localhost/botchat/chat/get_audio
#     # 从请求中获取conversation_id
#     conversation_id = request.data.get('conversation_id')
#     response = request.data.get('response_word')
#     # 根据conversation_id获取Conversation对象
#     latest_conversation = Conversation.objects.filter(id=conversation_id).first()
#     save_audio_from_xunfei(response, latest_conversation)  # 生成并保存音频
#     response_audio = convert_audio_to_base64(latest_conversation.response_audio)  # 读取数据库中的音频并转成base64格式
#     return Response({  # 返回响应
#         'response_voice': response_audio,
#     })


# ------------------------------------以下视图函数为前后端未分离前的视图函数------------------------------------
# ------------------------------------以下视图函数为前后端未分离前的视图函数------------------------------------

# @csrf_exempt
# def create_chat(request):
#     """
#     期望的接收值:
#     - 无特定参数，仅从cookie中获取token以校验和获取User对象。
#     功能介绍:
#     - 根据token确定用户身份并为其创建新的话题。
#     返回值:
#     - 成功: 返回新创建话题的相关数据的JSON响应。
#     - 失败: 返回一个表示错误的JSON响应。
#     """
#     token = request.COOKIES.get('token')  # 获取cookie中的token
#     user = obtain_user(token)
#     if not user:
#         return JsonResponse({'error': 'Invalid token or user not found.'}, status=401)
#     current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#     theme_name = f"{user.username}:{current_time}"
#     new_topic = Topic.objects.create(user=user, theme=theme_name)
#     new_topic.save()
#     topic_data = {
#         'id': new_topic.id,
#         'theme': new_topic.theme,
#     }
#     return JsonResponse({'topic': topic_data})
#
#
# @csrf_exempt
# def receive_text(request):
#     """
#     期望的接收值:
#     - POST请求。
#     - JSON格式的请求体，包含一个"text"字段。
#     功能介绍:
#     - 获取用户提供的文本并保存为一个对话(Conversation)。如果用户没有选择话题(即Session中没有topic_id)，则为其创建一个新话题(Topic)。
#     返回值:
#     - 成功: 返回相关的对话和话题数据。
#     - 失败: 返回一个表示错误的JSON响应。
#     """
#     if request.method == "POST":
#         token = request.COOKIES.get('token')
#         user = obtain_user(token)
#         if user is None:
#             return JsonResponse({'error': 'Invalid user'}, status=400)
#         data = json.loads(request.body.decode('utf-8'))
#         user_text = data.get('text')
#         topic_id = request.session.get('topic_id')
#         # 如果用户已选择主题
#         if topic_id:
#             try:
#                 topic = Topic.objects.get(id=topic_id)
#             except Topic.DoesNotExist:
#                 return JsonResponse({'error': 'Topic does not exist'}, status=400)
#             conversation = Conversation(topic=topic, prompt=user_text, response="")
#             conversation.save()
#             return JsonResponse({
#                 'type': 'existing_topic',
#                 'conversation': {
#                     'id': conversation.id,
#                     'prompt': conversation.prompt,
#                     'response': conversation.response
#                 }
#             })
#         # 如果用户未选择主题
#         else:
#             current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#             theme_name = f"{user.username}:{current_time}"
#             new_topic = Topic.objects.create(user=user, theme=theme_name)
#             conversation = Conversation(topic=new_topic, prompt=user_text, response="")
#             conversation.save()
#             # 存储新的topic_id到session中
#             request.session['topic_id'] = new_topic.id
#             topic_data = {
#                 'id': new_topic.id,
#                 'theme': new_topic.theme,
#             }
#             return JsonResponse({
#                 'type': 'new_topic',
#                 'topic': topic_data,
#                 'conversation': {
#                     'id': conversation.id,
#                     'prompt': conversation.prompt,
#                     'response': conversation.response
#                 }
#             })
#     return JsonResponse({'error': 'Invalid request'}, status=400)
#
#
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
#             converted_audio_file = convert_audio_format(audio_file)  # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
#             transcribed_text = audio_to_text(converted_audio_file)  # 将音频转换为文本
#             conversation = Conversation(topic=topic, prompt=transcribed_text)
#             conversation.save()
#             # asynchronously_save_audio_to_db.delay(conversation.id, converted_audio_file) #TODO 利用Celery实现异步存储音频文件,由于Docker尚未成功配置,因此暂时不使用Celery
#             asynchronously_save_audio_to_db(conversation.id, converted_audio_file)
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
#             converted_audio_file = convert_audio_format(audio_file)  # 转换音频格式为MP3(在前端实现MP3格式转换后该步骤可以省略)
#             transcribed_text = audio_to_text(converted_audio_file)  # 将音频转换为文本
#             conversation = Conversation(topic=topic, prompt=transcribed_text)
#             conversation.save()
#             # asynchronously_save_audio_to_db.delay(conversation.id, converted_audio_file) #TODO 利用Celery实现异步存储音频文件,由于Docker尚未成功配置,因此暂时不使用Celery
#             asynchronously_save_audio_to_db(conversation.id, converted_audio_file)
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
#
#
# @csrf_exempt
# def chat_with_openai(request):
#     """
#     期望的接收值:
#     - POST请求。
#     - JSON格式的请求体，包含一个"text"字段表示用户的提示。
#     功能介绍:
#     - 使用提供的提示与OpenAI聊天，并保存OpenAI的响应为一个对话。
#     返回值:
#     - 成功: 返回OpenAI的响应的JSON格式。
#     - 失败: 返回一个表示错误的JSON响应。
#     """
#     if request.method == 'POST':
#         # 从前端获取prompt
#         prompt = json.loads(request.body.decode('utf-8'))['text']
#         # 获取当前的topic_id
#         topic_id = request.session.get('topic_id')
#         # 1.获取历史聊天语境
#         message = obtain_context(topic_id)
#         # 2.将prompt与context结合以创建新的message
#         message.append({"role": "user", "content": prompt})
#         # 3.向openai发送请求并得到响应
#         response = obtain_openai_response(message)
#         # 4.将响应结果保存到数据库中
#         latest_conversation = Conversation.objects.filter(topic_id=topic_id).order_by('-created_time').first()
#         latest_conversation.response = response
#         latest_conversation.save()
#         # TODO 5.如果该topic下的conversation达到20的倍数,则尝试异步地更新context(目前异步更新context的功能还未实现
#         asynchronously_update_context(topic_id, message, latest_conversation)
#         # 5.生成的文本答复对应的语音答复，并保存到数据库中
#         save_audio_from_xunfei(response, latest_conversation)
#         response_audio = convert_audio_to_base64(latest_conversation.response_audio)
#         # 6.将响应结果返回给前端(如果有可能,将响应结果转为语音后同步发送给前端)
#         response_data = {
#             'id': latest_conversation.id,
#             'prompt': latest_conversation.prompt,
#             'response': latest_conversation.response,
#             'response_audio': response_audio,
#             'created_time': latest_conversation.created_time.strftime('%Y-%m-%d %H:%M:%S')
#         }
#         return JsonResponse({'conversation': response_data})
#     return JsonResponse({'error': 'Invalid request'}, status=400)
