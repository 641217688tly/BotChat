import shutil
import tempfile
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
BOT_ROLE_CONFIG = None


def load_whisper_model():  # 实现模型的预加载
    print(
        "load_whisper_model method is called, model is loading...This model is 2.9G in size and will take 3-5 minutes to download for the first time access.")
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


def convert_audio_format(audio_file, target_format='mp3'):  # 将前端传来的音频文件转换为mp3格式(LegendBug没用上)
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
    summarized_conversation_range = ((
                                             conversations.count() - 1) // UPDATE_CONTEXT_THRESHOLD) * UPDATE_CONTEXT_THRESHOLD  # 计算context所总结的conversation的范围,如果conversations.count()=0,结果也为0
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

def asynchronously_save_audio_to_db(conversation_id, audio_file):  # 由于存储大数据量的MP3文件耗时较多,因此选择异步地将音频文件保存到数据库中
    # 利用conversation_id获取conversation对象
    conversation = Conversation.objects.get(id=conversation_id)
    # 将mp3_audio_file存入conversation对象的prompt_audio字段中
    conversation.prompt_audio = audio_file
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


# 与文本转语音相关的函数:--------------------------------------------------------------------------------------------------
import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os


# 创建websocket对象
class Ws_Param(object):
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
        self.BusinessArgs = {"aue": "lame", "auf": "audio/L16;rate=16000", "vcn": "x4_lingxiaoying_em_v2",
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
def on_message(ws, message, conversation):
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
def on_error(ws, error):
    print("### websocket error:", error)


# 收到websocket关闭的处理
def on_close(ws):
    print("生成结束")


# 收到websocket连接建立的处理
def on_open_wrapper(ws, wsParam):
    def on_open():
        d = {
            "common": wsParam.CommonArgs,
            "business": wsParam.BusinessArgs,
            "data": wsParam.Data,
        }
        d = json.dumps(d)
        print("------>开始发送文本数据，生成音频")
        ws.send(d)

    thread.start_new_thread(on_open, ())


# 将文本发送至讯飞后，把收到的音频存储数据库中
def save_audio_from_xunfei(response_text, conversation):
    wsParam = Ws_Param(APPID='2fc3fd73', APISecret='NWQ3NzY3ZjU5NDhjNTgzZjFjYTZhYzll',
                       APIKey='11940ebd37b7f06d998750d55f1b576c',
                       Text=response_text)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    # 使用 functools.partial 来传递text到 on_message 函数
    on_message_with_arg = partial(on_message, conversation=conversation)
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message_with_arg, on_error=on_error, on_close=on_close)
    ws.on_open = lambda ws: on_open_wrapper(ws, wsParam)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


def convert_audio_to_base64(audio):
    return base64.b64encode(audio).decode('utf-8')
