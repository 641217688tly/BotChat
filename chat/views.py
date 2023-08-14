import json
import os
import shutil
import tempfile

from django.utils import timezone
from django.shortcuts import render
from chat.utils import *
from user.utils import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from chat.models import *


@csrf_exempt
def homepage(request):
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
                    'created_at': topic.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                topic_list.append(topic_data)
        print("homepage() method is handling AJAX request and return JsonResponse({'topics': topic_list})")
        return JsonResponse({'topics': topic_list})
    print("homepage() return render(request, 'chat/botchat.html')")
    return render(request, 'chat/botchat.html')


@csrf_exempt
def create_chat(request):
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
        'created_at': new_topic.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    return JsonResponse({'topic': topic_data})


@csrf_exempt
def change_theme(request):
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
                'created_at': new_topic.created_at.strftime('%Y-%m-%d %H:%M:%S')
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
            converted_audio_file = convert_audio_format(audio_file)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
                with open(temp_audio_path, 'wb') as temp_file:
                    shutil.copyfileobj(converted_audio_file, temp_file)
                transcribed_text = transcribe_audio(temp_audio_path)
                conversation = Conversation(topic=topic, prompt=transcribed_text)
                conversation.save()
            response_data = {
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response,
                    'created_at': conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')
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
            converted_audio_file = convert_audio_format(audio_file)
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
                with open(temp_audio_path, 'wb') as temp_file:
                    shutil.copyfileobj(converted_audio_file, temp_file)
                transcribed_text = transcribe_audio(temp_audio_path)
                conversation = Conversation(topic=topic, prompt=transcribed_text)
                conversation.save()
            response_data = {
                'conversation': {
                    'id': conversation.id,
                    'prompt': conversation.prompt,
                    'response': conversation.response,
                    'created_at': conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')
                },
                'topic': {
                    'id': topic.id,
                    'theme': topic.theme,
                    'created_at': topic.created_at.strftime('%Y-%m-%d %H:%M:%S')
                },
                'type': 'new_topic'
            }
        return JsonResponse(response_data)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def chat_with_openai(request):
    if request.method == 'POST':
        # 从前端获取prompt
        prompt = json.loads(request.body.decode('utf-8'))['text']
        print("prompt: " + prompt)
        # TODO 1.获取历史聊天记录
        context = obtain_context()
        # TODO 2.创建新的message
        messages = joint_message(context, prompt)
        # TODO 3.向openai发送请求并得到响应
        response = obtain_openai_response(messages)
        # TODO 4.将响应结果保存到数据库中
        # 获取当前的User和theme
        topic_id = request.session.get('topic_id')
        latest_conversation = Conversation.objects.filter(topic_id=topic_id).order_by('-created_time').first()
        latest_conversation.response = response
        latest_conversation.save()
        # TODO 5.将响应结果返回给前端(如果有可能,将响应结果转为语音后同步发送给前端)
        return JsonResponse({'response': response})
    return JsonResponse({'error': 'Invalid request'}, status=400)
