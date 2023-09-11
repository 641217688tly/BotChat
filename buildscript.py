# preload_model.py
from faster_whisper import WhisperModel

# 用于在构建项目镜像时下载模型
def load_whisper_model_during_build():
    print("load_whisper_model_during_build method is called, model is loading...This model is 2.9G in size and will take 3-5 minutes to download for the first time access.")
    model_size = "large-v2"
    _ = WhisperModel(model_size, device="cuda", compute_type="float16")  # 我们这里不需要设置全局变量，只要确保模型被下载即可。
    print("Model successfully loaded!")

if __name__ == "__main__":
    load_whisper_model_during_build()
