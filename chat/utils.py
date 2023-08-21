import os
import shutil
import tempfile

import openai
import yaml

from chat.celery import app
from chat.models import *
from faster_whisper import WhisperModel
from pydub import AudioSegment


# 与加载模型和参数相关的函数:-----------------------------------------------------------------------------------------------

WHISPER_MODEL = None
OPENAI_API_KEY = None
UPDATE_CONTEXT_THRESHOLD = None  # 规定了更新context的阈值,即当theme的聊天记录达到20条时,就更新context
BOT_ROLE_CONFIG = None

def load_whisper_model():  # 实现模型的预加载
    print("load_whisper_model method is called, model is loading...This model is 2.9G in size and will take 3-5 minutes to download for the first time access.")
    global WHISPER_MODEL
    model_size = "large-v2"
    WHISPER_MODEL = WhisperModel(model_size, device="cuda", compute_type="float16")
    print("Model successfully loaded!")

def load_config_constant():  # 加载YAML配置文件
    global OPENAI_API_KEY, UPDATE_CONTEXT_THRESHOLD, BOT_ROLE_CONFIG
    # 加载YAML配置文件
    with open('config.yml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    # 从配置中获取值
    OPENAI_API_KEY = config['OPENAI_API_KEY']
    UPDATE_CONTEXT_THRESHOLD = config['UPDATE_CONTEXT_THRESHOLD']
    BOT_ROLE_CONFIG = config['BOT_ROLE_CONFIG']


# 与语音识别转录相关的函数:-------------------------------------------------------------------------------------------------


def audio_to_text(mp3_audio_file):
    """
    Transcribes an audio file and returns the transcribed text.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
        with open(temp_audio_path, 'wb') as temp_file:
            shutil.copyfileobj(mp3_audio_file, temp_file)
        transcribed_text = transcribe_audio(temp_audio_path)
    return transcribed_text


def transcribe_audio(audio_file_path):
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        load_whisper_model()
    segments, info = WHISPER_MODEL.transcribe(audio_file_path, beam_size=5)
    segments = list(segments)
    transcription = ' '.join([segment.text for segment in segments])
    return transcription


def convert_audio_format(audio_file, target_format='mp3'):  # 将前端传来的音频文件转换为mp3格式
    # 此处可添加转换音频格式的代码
    audio_segment = AudioSegment.from_file(audio_file)
    converted_audio_file = audio_segment.export(format=target_format)
    print("converted_audio_file method is called")
    return converted_audio_file


# 与openAI交互相关的函数:--------------------------------------------------------------------------------------------------

def obtain_context(topic_id):  # 创建context
    context = [
        {"role": "system",
         "content": BOT_ROLE_CONFIG},
    ]
    topic = Topic.objects.get(id=topic_id)
    topic_context = topic.context
    if topic_context != '':  # 如果context不为空(即conversation的数大于20),则将context添加到message中
        context.append({"role": "system", "content": topic_context})
    conversations = topic.conversations.all()
    summarized_conversation_range = (( conversations.count() - 1) // UPDATE_CONTEXT_THRESHOLD) * UPDATE_CONTEXT_THRESHOLD  # 计算context所总结的conversation的范围,如果conversations.count()=0,结果也为0
    remainder = conversations.count() - summarized_conversation_range  # 计算未被总结进context的conversation的个数
    if remainder > 0:
        # 获取最后的remainder条对话
        last_conversations = list(conversations)[-remainder:]
        for conversation in last_conversations:
            # 检查当前对话是否是最后一条conversation，并且是没有response的对话，如果是，则跳过
            if conversation == last_conversations[-1] and not conversation.response:
                continue
            # 向message中添加对话
            context.append({"role": "user", "content": conversation.prompt})
            if conversation.response:
                context.append({"role": "assistant", "content": conversation.response})
    return context


def asynchronously_update_context(topic_id, message, latest_conversation):  # TODO 更新context(暂未实现异步更新)
    topic = Topic.objects.get(id=topic_id)
    conversations = topic.conversations.all()
    if conversations.count() % UPDATE_CONTEXT_THRESHOLD == 0:
        if latest_conversation.response is not None:
            message.append({"role": "assistant", "content": latest_conversation.response})
        message.append({"role": "user",
                        "content": "Please summarize the context and content of your previous conversation with the user. The summary text should contain the main information of the user, the main context and details of the conversation. The summarized text should be limited to 250 words"})
        updated_context = obtain_openai_response(message)
        topic.context = updated_context
        topic.save()


def obtain_openai_response(message):
    openai.api_key = OPENAI_API_KEY
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
        )
        return response.choices[0].message['content'].strip()
    except (Exception):
        return "Error: Response timed out, please check your network connection!"


# 数据库增删改查:---------------------------------------------------------------------------------------------------------

def asynchronously_save_audio_to_db(conversation_id, mp3_audio_file): # 由于存储大数据量的MP3文件耗时较多,因此选择异步地将音频文件保存到数据库中
    # 利用conversation_id获取conversation对象
    conversation = Conversation.objects.get(id=conversation_id)
    # 将mp3_audio_file存入conversation对象的prompt_audio字段中
    conversation.prompt_audio = mp3_audio_file
    # 保存conversation对象
    conversation.save()


# @app.task #TODO 利用Celery实现异步存储音频文件,由于Docker尚未成功配置,因此暂时不使用Celery
# def asynchronously_save_audio_to_db(conversation_id, mp3_audio_file): # 由于存储大数据量的MP3文件耗时较多,因此选择异步地将音频文件保存到数据库中
#     # 利用conversation_id获取conversation对象
#     conversation = Conversation.objects.get(id=conversation_id)
#     # 将mp3_audio_file存入conversation对象的prompt_audio字段中
#     conversation.prompt_audio = mp3_audio_file
#     # 保存conversation对象
#     conversation.save()




