from django.urls import path
from chat.views import *

urlpatterns = [
    path('gettopics/', get_topics),  # 获取用户的所有topic
    path('getdetails/', get_topic_details),  # 获取用户指定topic下的所有conversation
    path('get_audio_assessment/', get_audio_assessment),  # 获取用户的语音评估结果
    path('get_expression_assessment/', get_expression_assessment),  # 获取用户的英语表达的评估结果
    path('newtopic/', create_topic),  # 为用户创建新的topic
    path('customtopic/', create_user_defined_topic),  # 为用户创建用户自定义语境的topic
    path('preset_topic/', create_preset_topic),  # 为用户创建已经预设过语境的topic
    path('change/theme/', update_topic_theme),  # 修改topic的theme字段
    path('rerecord_voice/', rerecord_voice),  # 重新录制用户的语音(prompt_audio)

    path('sendvoice/', receive_audio),  # 接收用户发送的语音,转为文本后作为prompt与openai交互,将响应结果合成为语音输出(未拆分版本)
    path('sendword/', receive_text),  # 将用户发送的文本作为prompt与openai交互,将响应结果合成为语音输出(未拆分版本)
    # 将上述两个视图函数拆分为以下视图函数:
    path('handle_audio/', handle_audio),
    path('obtain_openai_response/', chat_with_openai),
    path('tts/', text_to_speech)
]
