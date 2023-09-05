import functools
import shutil
import tempfile
import os
from io import BytesIO
from functools import partial
import openai
import yaml
from faster_whisper import WhisperModel
from pydub import AudioSegment
from chat.models import *

# 与加载模型和参数相关的函数:-----------------------------------------------------------------------------------------------

WHISPER_MODEL = None
OPENAI_API_KEY = None
UPDATE_CONTEXT_THRESHOLD = None  # 规定了更新context的阈值,即当theme的聊天记录达到20条时,就更新context


def load_whisper_model():  # 实现模型的预加载
    print(
        "load_whisper_model method is called, model is loading...This model is 2.9G in size and will take 3-5 minutes to download for the first time access.")
    global WHISPER_MODEL
    model_size = "large-v2"
    WHISPER_MODEL = WhisperModel(model_size, device="cuda", compute_type="float16")  # float16
    print("Model successfully loaded!")


def load_config_constant():  # 加载YAML配置文件
    global OPENAI_API_KEY, UPDATE_CONTEXT_THRESHOLD, DEFAULT_TOPIC_CONTEXT
    # 加载YAML配置文件
    with open('config.yml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    # 从配置中获取值
    OPENAI_API_KEY = config['OPENAI_API_KEY']
    UPDATE_CONTEXT_THRESHOLD = config['UPDATE_CONTEXT_THRESHOLD']


# 与语音识别转录相关的函数:-------------------------------------------------------------------------------------------------

def convert_audio_format(prompt_audio_binary_data, target_format='mp3'):  # 接收二进制格式的音频文件,并将其转换为mp3格式
    audio_segment = AudioSegment.from_file(BytesIO(prompt_audio_binary_data))
    converted_audio_file = BytesIO()
    audio_segment.export(converted_audio_file, format=target_format)
    converted_audio_file.seek(0)
    return converted_audio_file


def transcribe_audio(audio_file_path):  # 调用faster-whisper模型进行语音识别
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        load_whisper_model()
    segments, info = WHISPER_MODEL.transcribe(audio_file_path, beam_size=5)
    segments = list(segments)
    transcription = ' '.join([segment.text for segment in segments])
    return transcription


def audio_to_text(prompt_audio_binary_data):  # 临时存储音频文件并调用transcribe_audio函数进行语音识别
    """
    Transcribes an audio file and returns the transcribed text.
    """
    mp3_audio_file = convert_audio_format(prompt_audio_binary_data)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_audio_path = os.path.join(temp_dir, 'temp_audio.mp3')
        with open(temp_audio_path, 'wb') as temp_file:
            shutil.copyfileobj(mp3_audio_file, temp_file)
        transcribed_text = transcribe_audio(temp_audio_path)
    return transcribed_text


# 与openAI交互相关的函数:--------------------------------------------------------------------------------------------------

def obtain_message(topic_id, prompt):  # 创建context
    topic = Topic.objects.get(id=topic_id)
    message = [
        {"role": "system",
         "content": topic.custom_context},
    ]
    topic_context = topic.context
    if topic_context != '':  # 如果context不为空(即conversation的数大于20),则将context添加到message中
        message.append({"role": "system", "content": topic_context})
    conversations = topic.conversations.all()
    summarized_conversation_range = (
                                            conversations.count() // UPDATE_CONTEXT_THRESHOLD) * UPDATE_CONTEXT_THRESHOLD  # 计算context所总结的conversation的范围,如果conversations.count()=0,结果也为0
    remainder = conversations.count() - summarized_conversation_range  # 计算未被总结进context的conversation的个数
    if remainder > 0:
        # 获取最后的remainder条对话
        last_conversations = list(conversations)[-remainder:]
        for conversation in last_conversations:
            # 向message中添加对话
            if conversation.prompt is not None:
                message.append({"role": "user", "content": conversation.prompt})
            if conversation.response is not None:
                message.append({"role": "assistant", "content": conversation.response})
    # 将本次用户提问的prompt添加到message中
    message.append({"role": "user", "content": prompt})
    return message

from celery import shared_task

# @shared_task
def asynchronously_update_context(topic_id, message, conversation_id):  # TODO 更新context(暂未实现异步更新)
    print("asynchronously_update_context method is called")
    new_conversation = Conversation.objects.get(id=conversation_id)
    topic = Topic.objects.get(id=topic_id)
    conversations = topic.conversations.all()
    if conversations.count() % UPDATE_CONTEXT_THRESHOLD == 0:
        if new_conversation.response is not None:
            message.append({"role": "assistant", "content": new_conversation.response})
        message.append({"role": "user",
                        "content": "Please summarize the context and content of your previous conversation with the user. The summary text should contain the main information of the user, the main context and details of the conversation. The summarized text should be limited to 250 words"})
        updated_context = obtain_openai_response(message)
        topic.context = updated_context
        topic.save()
    print("asynchronously_update_context method is finished")


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


# 对于Conversation模型的操作有可能需要使用乐观锁
# @shared_task
def asynchronously_obtain_audio_assessment_embellished_by_openai(prompt, prompt_audio, conversation_id):  # 获取音频评估
    print("asynchronously_obtain_audio_assessment_embellished_by_openai method is called")
    new_conversation = Conversation.objects.get(id=conversation_id)
    audio_assessment_prompt = assess_audio_from_xunfei(prompt, prompt_audio)
    message = [
        {"role": "user", "content": audio_assessment_prompt},
        {"role": "user", "content": settings.AUDIO_ASSESSMENT_REQUIREMENT_PROMPT},
    ]
    openai.api_key = OPENAI_API_KEY
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message,
        )
        audio_assessment_text = response.choices[0].message['content'].strip()
        new_conversation.audio_assessment = audio_assessment_text
        new_conversation.save()
        print("asynchronously_obtain_audio_assessment_embellished_by_openai method is finished")
        return
    except (Exception):
        print("asynchronously_obtain_audio_assessment_embellished_by_openai method is finished")
        return "Error: Response timed out, please check your network connection!"


# 与文本转语音相关的函数:--------------------------------------------------------------------------------------------------

# 创建TTS对应的websocket对象
class WsParamTTS(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数，更多个性化参数可在官网查看
        # TODO 此处可继续定制发音人、音量、语速等，可考虑自定义（没钱）
        self.BusinessArgs = {"aue": "lame", "auf": "audio/L16;rate=16000", "vcn": "x2_enus_catherine",
                             "tte": "utf8", "sfl": 1, "speed": 30}
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}

    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url


# 处理收到websocket的音频文件
def on_message_TTS(ws, message, conversation):
    try:
        message = json.loads(message)
        code = message["code"]
        sid = message["sid"]
        audio = message["data"]["audio"]
        audio = base64.b64decode(audio)
        status = message["data"]["status"]
        if status == 2:
            print("ws is closed")
            ws.close()
        if code != 0:
            errMsg = message["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
        else:
            # 写入音频文件到指定位置conversation.response_audio
            response_audio = conversation.response_audio
            conversation.response_audio = response_audio + audio
            conversation.save()
    except Exception as e:
        print("receive msg,but parse exception:", e)


# 收到websocket错误的处理
def on_error(error):
    print("### websocket error:", error)


# 收到websocket关闭的处理
def on_close_TTS():
    print("------>生成结束")


# 收到websocket连接建立的处理
def on_open_wrapper_TTS(ws, ws_param):
    def on_open():
        d = {
            "common": ws_param.CommonArgs,
            "business": ws_param.BusinessArgs,
            "data": ws_param.Data,
        }
        d = json.dumps(d)
        print("------>开始发送文本数据，生成音频")
        ws.send(d)

    thread.start_new_thread(on_open, ())


# 将文本发送至讯飞后，把收到的音频存储数据库中
def save_audio_from_xunfei(response_text, conversation):
    ws_param = WsParamTTS(APPID='2fc3fd73', APISecret='NWQ3NzY3ZjU5NDhjNTgzZjFjYTZhYzll',
                          APIKey='11940ebd37b7f06d998750d55f1b576c',
                          Text=response_text)
    websocket.enableTrace(False)
    ws_url = ws_param.create_url()
    # 使用 functools.partial 来传递text到 on_message 函数
    on_message_with_arg = partial(on_message_TTS, conversation=conversation)
    ws = websocket.WebSocketApp(ws_url, on_message=on_message_with_arg, on_error=on_error, on_close=on_close_TTS)
    ws.on_open = lambda ws: on_open_wrapper_TTS(ws, ws_param)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


def convert_audio_to_base64(binary_audio_data):
    return base64.b64encode(binary_audio_data).decode('utf-8')  # 将二进制音频数据转换为base64编码的字符串


# 与语音评价相关的函数:--------------------------------------------------------------------------------------------------
from builtins import Exception, str

import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识
received_xml = None


class WsParamISE(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, AudioFile, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.AudioFile = AudioFile
        self.Text = Text

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"category": "read_chapter",  # TODO 评分模式，可自定义
                             "sub": "ise", "ent": "en_vip", "cmd": "ssb", "auf": "audio/L16;rate=16000",
                             "aue": "lame", "text": self.Text, "ttp_skip": True, "aus": 1}

    # 生成url
    def create_url(self):
        # wws请求对Python版本有要求，py3.7可以正常访问，如果py版本请求wss不通，可以换成ws请求，或者更换py版本
        url = 'ws://ise-api.xfyun.cn/v2/open-ise'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ise-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/open-ise " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ise-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url


# 收到websocket消息的处理
def on_message_ISE(ws, message):
    try:
        code = json.loads(message)["code"]
        sid = json.loads(message)["sid"]
        if code != 0:
            errMsg = json.loads(message)["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
        else:
            data = json.loads(message)["data"]
            status = data["status"]
            result = data["data"]
            if (status == 2):
                xml = base64.b64decode(result)
                global received_xml
                received_xml = xml.decode("gbk")

    except Exception as e:
        print("receive msg,but parse exception:", e)


# 收到websocket关闭的处理
def on_close_ISE():
    print("------>评分生成结束")


# 收到websocket连接建立的处理
def on_open_wrapper_ISE(ws, ws_param):
    def on_open():
        frameSize = 1280  # 每一帧的音频大小
        interval = 0.04  # 发送音频间隔(单位:s)
        status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧
        audio_data = ws_param.AudioFile
        current_pos = 0

        while True:
            # 从音频数据中读取一帧数据
            buf = audio_data[current_pos:current_pos + frameSize]
            current_pos += frameSize
            # 文件结束
            if not buf:
                status = STATUS_LAST_FRAME
            # 发送第一帧音频，带business参数
            if status == STATUS_FIRST_FRAME:
                d = {"common": ws_param.CommonArgs,
                     "business": ws_param.BusinessArgs,
                     "data": {"status": 0}}
                d = json.dumps(d)
                ws.send(d)
                status = STATUS_CONTINUE_FRAME
            # 中间帧处理
            elif status == STATUS_CONTINUE_FRAME:
                d = {"business": {"cmd": "auw", "aus": 2, "aue": "lame"},
                     "data": {"status": 1, "data": buf}}
                ws.send(json.dumps(d))
            # 最后一帧处理
            elif status == STATUS_LAST_FRAME:
                d = {"business": {"cmd": "auw", "aus": 4, "aue": "lame"},
                     "data": {"status": 2, "data": buf}}
                ws.send(json.dumps(d))
                time.sleep(5)
                break
            # 模拟音频采样间隔
            time.sleep(interval)
        ws.close()

    thread.start_new_thread(on_open, ())


def assess_audio_from_xunfei(prompt, prompt_audio):
    TEXT = '\uFEFF' + prompt
    wsParam = WsParamISE(APPID='2fc3fd73', APISecret='NWQ3NzY3ZjU5NDhjNTgzZjFjYTZhYzll',
                         APIKey='11940ebd37b7f06d998750d55f1b576c',
                         AudioFile=prompt_audio,
                         Text=TEXT)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message_ISE, on_error=on_error, on_close=on_close_ISE)
    on_open_with_param = functools.partial(on_open_wrapper_ISE, ws_param=wsParam)
    ws.on_open = on_open_with_param
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    global received_xml
    return received_xml
