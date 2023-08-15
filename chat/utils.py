import openai
import yaml
from chat.models import *
import whisper
from faster_whisper import WhisperModel
from pydub import AudioSegment

# 加载YAML配置文件
with open('config.yml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)
# 从配置中获取JWT密钥
OPENAI_API_KEY = config['OPENAI_API_KEY']
UPDATE_CONTEXT_THRESHOLD = config['UPDATE_CONTEXT_THRESHOLD']  # 规定了更新context的阈值,即当theme的聊天记录达到20条时,就更新context

def transcribe_audio(audio_file_path):
    model_size = "large-v2"
    model = WhisperModel(model_size, device="cuda", compute_type="float16")
    # TODO 或许可以在Session开启时/服务器启动时就加载模型,这样可以避免每次都加载模型的时间开销
    segments, info = model.transcribe(audio_file_path, beam_size=5)
    segments = list(segments)
    transcription = ' '.join([segment.text for segment in segments])
    return transcription


def convert_audio_format(audio_file, target_format='mp3'):  # 将前端传来的音频文件转换为mp3格式
    # 此处可添加转换音频格式的代码
    audio_segment = AudioSegment.from_file(audio_file)
    converted_audio_file = audio_segment.export(format=target_format)
    print("converted_audio_file method is called")
    return converted_audio_file

# def transcribe_audio(audio_file_path):
#     model = whisper.load_model("medium").to("cuda")  # 加载medium模型并将其放到GPU上
#     result = model.transcribe(audio_file_path, fp16=False)
#     transcription = result["text"]
#     return transcription
#
#
# def convert_audio_format(audio_file, target_format='mp3'):
#     # 将前端传来的音频文件转换为mp3格式
#     audio_segment = AudioSegment.from_file(audio_file)
#     converted_audio_file = audio_segment.export(format=target_format)
#     print("converted_audio_file method is called")
#     return converted_audio_file


def obtain_context(topic_id):  # 创建context
    context = [
        {"role": "system",
         "content": "You are an oral English teacher fluent in both Chinese and English. The following system content is the former conversation bewteen user and you."},
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


def obtain_openai_response(message):  # 接收message,向openai发送请求并得到响应
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message,
    )
    return response.choices[0].message['content'].strip()
