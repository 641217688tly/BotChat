from django.core.files.base import ContentFile
from django.utils import timezone
from chat.utils import *
from chat.serializers import *
from chat.models import *
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def create_topic(request):  # localhost/botchat/chat/newtopic/ 为用户创建新的topic
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
    return Response({"topics": serializer.data}, status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def create_user_defined_topic(request):  # localhost/botchat/chat/customtopic/ 为用户创建自定义聊天语境的topic
    # 接收前端的数据
    data = request.data
    # 验证用户身份
    user_id = data.get('user_id', None)
    if user_id is None:
        return Response({'error': 'user_id is required!'}, status=status.HTTP_400_BAD_REQUEST)
    # 获取用户
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=status.HTTP_400_BAD_REQUEST)
    # 检验必填数据的完整性
    required_fields = [
        'user_id',
        'topic_theme',
        'conversation_time',
        'conversation_location',
        'conversation_scene',
        'user',
        'bot',
        'user.role',
        'bot.role',
        'user.personality',
        'bot.personality'
    ]
    for field in required_fields:
        keys = field.split('.')
        value = data
        for key in keys:
            value = value.get(key, None)
            if value is None:
                return Response({'error': f'Missing required field: {field}'}, status=status.HTTP_400_BAD_REQUEST)
    # 创建Topic
    descriptive_texts = {
        'conversation_time': 'Chat time is: ',
        'conversation_location': 'Chat location is: ',
        'conversation_scene': 'Chat scene is: ',
        'instructions': 'Special instructions: ',
        'other_information': 'Other information: '
    }
    custom_context_items = []
    for key, text in descriptive_texts.items():
        if data.get(key):
            custom_context_items.append(f"{text}{data[key]}")
    user_data = data['user']
    for key, value in user_data.items():
        if value and key not in ['role', 'personality']:
            custom_context_items.append(f"User's {key}: {value}")
        elif key == 'personality':
            custom_context_items.append(f"User's personality: {', '.join(value)}")
    bot_data = data['bot']
    for key, value in bot_data.items():
        if value and key not in ['role', 'personality']:
            custom_context_items.append(f"Bot's {key}: {value}")
        elif key == 'personality':
            custom_context_items.append(f"Bot's personality: {', '.join(value)}")
    custom_context = '; '.join(custom_context_items)
    new_topic = Topic(
        user=user,
        theme=data['topic_theme'],
        custom_context=custom_context
    )
    new_topic.save()
    # 若predefined_conversations不为空,则以刚刚创建的Topic的id为外键,在此基础上创建Conversation对象
    predefined_conversations = data.get('predefined_conversations', {})
    user_msgs = predefined_conversations.get('user', [])
    bot_msgs = predefined_conversations.get('bot', [])
    if (user_msgs is not None) and (bot_msgs is not None) and len(user_msgs) == len(bot_msgs):
        for i in range(len(user_msgs)):
            convo = Conversation(
                topic=new_topic,
                prompt=user_msgs[i],
                response=bot_msgs[i]
            )
            convo.save()
    # 返回响应
    serializer = TopicSerializer(new_topic)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def change_theme(request):  # localhost/botchat/chat/change/theme/ 为用户切换当天聊天的topic
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


@api_view(['GET'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def get_topics(request):  # localhost/botchat/chat/gettopics/?user_id 为用户获取所有的历史聊天topic
    user_id = request.GET.get('user_id')
    if user_id is None:
        return Response({"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    # 获取用户相关的topic
    topics = Topic.objects.filter(user__id=user_id)  # 通过外键user__id跨关系查询与该用户相关的topic
    # 序列化这些topic
    serializer = TopicSerializer(topics, many=True)
    return Response({"topics": serializer.data})


@api_view(['GET'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def get_topic_details(request):  # localhost/botchat/chat/getdetails/?topic_id 为用户获取某个topic下的所有历史对话
    # 获取GET参数中的topic_id
    topic_id = request.GET.get('topic_id')
    if not topic_id:
        return Response({'error': 'Missing topic_id parameter'}, status=400)
    # 查询对应的Conversations
    conversations = Conversation.objects.filter(topic__id=topic_id)
    # # 序列化数据
    # serializer = ConversationSerializer(conversations, many=True)
    # serialized_data = serializer.data
    # # 构造新的JSON结构以符合前端的需求
    # details = []
    # for item in serialized_data:
    #     detail = {
    #         'detail_id': item['conversation_id'],
    #         'prompt': item['prompt_word'],
    #         'response_word': item['response_word'],
    #         'response_voice': item['response_voice']
    #     }
    #     details.append(detail)
    details = []
    for conversation in conversations:
        detail = {
            'detail_id': conversation.id,
            'prompt': conversation.prompt,
            'response_word': conversation.response,
            'response_voice': convert_audio_to_base64(conversation.response_audio)
        }
        details.append(detail)
    return Response({'details': details})


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def receive_text(request):  # localhost/botchat/chat/sendword/ 接收用户发送的文字prompt
    # 从请求中获取数据:
    user_id = request.data.get('user_id')
    prompt = request.data.get('prompt_word')
    topic_id = request.data.get('topic_id')

    # 确保数据完整性
    if (user_id and prompt and topic_id) is None:
        return Response({'error': 'Missing required data!'}, status=400)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=400)

    # 根据topic_id的正负值判断是否为用户创建新的topic或者使用已有的topic
    if topic_id == '-1':  # 创建新的Topic
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        theme_name = f"{user.username}:{current_time}"
        topic = Topic.objects.create(user=user, theme=theme_name)
        topic_id = topic.id  # 更新topic_id为新创建的Topic的id
    else:
        topic = Topic.objects.filter(id=topic_id).first()
        if topic is None:
            return Response({'error': 'Invalid topic'}, status=400)

    # 创建新的Conversation,以存储用户的输入prompt以及后续需要保存的response + response_audio
    new_conversation = Conversation.objects.create(
        topic=topic,
        prompt=prompt,
        response_audio=b''
    )
    new_conversation.save()

    # 将用户输入的音频转为的文字作为prompt与openai进行交互,得到response
    message = obtain_message(topic_id, prompt)  # 获取历史聊天语境
    response = obtain_openai_response(message)  # 向openai发送请求并得到响应
    new_conversation.response = response  # 将response存入数据库

    # 使用响应文本合成音频并存入数据库
    save_audio_from_xunfei(response,new_conversation)  # 生成并保存音频进数据库(包含了new_conversation.response_audio = response_audio)
    new_conversation.save()

    # 读取数据库中的音频并转成base64格式的字符串
    response_audio_base64_data = convert_audio_to_base64(new_conversation.response_audio)

    # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(TODO 目前异步更新context的功能还未实现)
    asynchronously_update_context(topic_id, message, new_conversation)
    # asynchronously_update_context.delay(topic_id, message, new_conversation.id)

    return Response({  # 返回响应
        'response_word': response,
        'response_voice': response_audio_base64_data,
        'topic_id': topic_id
    })


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def receive_audio(request):  # localhost/botchat/chat/sendvoice/ 接收用户发送的语音prompt
    # 从请求中获取数据:
    user_id = request.data.get('user_id')
    prompt_audio = request.data.get('prompt_voice')  # 接收到的是base64格式的音频文件的字符串
    topic_id = request.data.get('topic_id')

    # 确保数据完整性
    if (user_id and prompt_audio and topic_id) is None:
        return Response({'error': 'Missing required data!'}, status=400)
    user = User.objects.filter(id=user_id).first()
    if user is None:
        return Response({'error': 'Invalid user'}, status=400)

    # 根据topic_id的正负值判断是否为用户创建新的topic或者使用已有的topic
    if topic_id == '-1':  # 创建新的Topic
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        theme_name = f"{user.username}:{current_time}"
        topic = Topic.objects.create(user=user, theme=theme_name)
        topic_id = topic.id  # 更新topic_id为新创建的Topic的id
    else:
        topic = Topic.objects.filter(id=topic_id).first()
        if topic is None:
            return Response({'error': 'Invalid topic'}, status=400)

    # 处理音频数据,得到二进制格式的音频数据
    prompt_audio_binary_data = base64.b64decode(prompt_audio)  # 将Base64格式的音频字符串转换为二进制数据

    # 将音频转换为文本(耗时较长)
    prompt = audio_to_text(prompt_audio_binary_data)

    # 创建新的Conversation,以存储用户的输入prompt + prompt_audio以及后续需要保存的response + response_audio + prompt_audio_assessment
    new_conversation = Conversation.objects.create(
        topic=topic,
        prompt=prompt,
        prompt_audio=prompt_audio_binary_data,
        response_audio=b'',
    )
    new_conversation.save()

    # 利用科大讯飞API+openaiAPI对用户输入的音频进行评分(耗时较长 TODO 应该异步地实现)
    asynchronously_obtain_audio_assessment_embellished_by_openai(prompt, prompt_audio, new_conversation)
    # asynchronously_obtain_audio_assessment_embellished_by_openai.delay(prompt, prompt_audio, new_conversation.id)

    print("receive_audio view function is successfully skipping the asynchronous function!")

    # 将用户输入的音频转为的文字作为prompt与openai进行交互,得到response
    message = obtain_message(topic_id, prompt)  # 获取历史聊天语境
    response = obtain_openai_response(message)  # 向openai发送请求并得到响应
    new_conversation.response = response  # 将response存入数据库

    # 使用响应文本合成音频并存入数据库
    save_audio_from_xunfei(response,new_conversation)  # 生成并保存音频进数据库(包含了new_conversation.response_audio = response_audio)
    new_conversation.save()

    # 读取数据库中的音频并转成base64格式的字符串
    response_audio_base64_data = convert_audio_to_base64(new_conversation.response_audio)

    # 如果该topic下的conversation达到20的倍数,则尝试异步地更新context(TODO 目前异步更新context的功能还未实现)
    asynchronously_update_context(topic_id, message, new_conversation)
    # asynchronously_update_context.delay(topic_id, message, new_conversation.id)

    print("receive_audio view function is successfully skipping the asynchronous function!")

    return Response({  # 返回响应
        'response_word': response,
        'response_voice': response_audio_base64_data,
        'topic_id': topic_id
    })


@api_view(['POST'])
@permission_classes([]) # @permission_classes([IsAuthenticated])
def rerecord_voice(request):  # localhost/botchat/chat/rerecord_voice/ 为用户重新录制某个topic下的某一prompt的语音
    # 获取请求中的conversation_id和新的prompt_voice
    conversation_id = request.data.get('conversation_id')
    new_prompt_voice = request.data.get('prompt_voice')
    # 检查是否提供了必要的数据
    if all([conversation_id, new_prompt_voice]) is None:
        return Response({
            'success': False,
            'message': 'Missing required data!'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 查找相应的Conversation
    conversation = Conversation.objects.filter(id=conversation_id).first()
    if conversation is None:
        return Response({
            'success': False,
            'message': 'Invalid conversation ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    # 更新Conversation的prompt_audio字段
    audio_file = ContentFile(new_prompt_voice.read())
    conversation.prompt_audio = audio_file
    conversation.save()
    return Response({
        'success': True,
        'message': 'Voice replaced successfully'
    }, status=status.HTTP_200_OK)

# ------------------------------------将获取openai响应与合成语音的功能进行拆分------------------------------------
# ------------------------------------将获取openai响应与合成语音的功能进行拆分------------------------------------

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def receive_text(request):  # localhost/botchat/chat/sendword/
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
#     message = obtain_message(topic_id, prompt)  # 获取历史聊天语境
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
# def receive_audio(request):  # localhost/botchat/chat/sendvoice/  # TODO 音频转文字这部分会耗时3-5秒,可以从receive_audio中再进行拆分
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
#     message = obtain_message(topic_id, prompt)  # 获取历史聊天语境
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
# def send_audio(request):  # localhost/botchat/chat/get_audio/
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
