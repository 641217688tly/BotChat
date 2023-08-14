import openai
import yaml
from faster_whisper import WhisperModel
from pydub import AudioSegment

# 加载YAML配置文件
with open('config.yml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)
# 从配置中获取JWT密钥
OPENAI_API_KEY = config['OPENAI_API_KEY']
UPDATE_CONTEXT_THRESHOLD = 20 # 规定了更新context的阈值,即当theme的聊天记录达到5条时,就更新context

def transcribe_audio(audio_file_path):
    model_size = "large-v2"
    model = WhisperModel(model_size, device="cuda", compute_type="float16")
    #TODO 或许可以在Session开启时/服务器启动时就加载模型,这样可以避免每次都加载模型的时间开销
    segments, _ = model.transcribe(audio_file_path, beam_size=5)
    segments = list(segments)
    transcription = ' '.join([segment.text for segment in segments])
    return transcription


def convert_audio_format(audio_file, target_format='mp3'):  # 将前端传来的音频文件转换为mp3格式
    # 此处可添加转换音频格式的代码
    audio_segment = AudioSegment.from_file(audio_file)
    converted_audio_file = audio_segment.export(format=target_format)
    return converted_audio_file


def obtain_context(): #TODO 用于根据当前theme的聊天记录的个数来获取context或context + historical chat,以及是否异步地向openai发送请求以更新context

    return


def asynchronously_update_context(): #TODO 异步地向openai发送请求以更新context(可能需要用到joint_message())

    return


def joint_message(context, prompt): #TODO 接收context和prompt然后拼接成一个完整的message

    return


def obtain_openai_response(messages): #TODO 接收message,向openai发送请求并得到响应
    openai.api_key = "OPENAI_API_KEY"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
    )
    return response.choices[0].message['content'].strip()