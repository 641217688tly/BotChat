# 基础镜像
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# 设置环境变量，确保 Python 输出直接到终端，不使用任何缓冲
ENV PYTHONUNBUFFERED 1

# 创建目录并设置工作目录
RUN mkdir /code
WORKDIR /code

# 安装系统级依赖
RUN apt-get update && \
    apt-get install -y --fix-missing -y \
    gcc \
    build-essential \
    libmariadb-dev-compat \
    libmariadb-dev \
    libssl-dev \
    pkg-config \
    ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 安装CUDA 11.8
#RUN apt-get install -y gnupg2 && \
#    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/debian10/x86_64/ /" | tee /etc/apt/sources.list.d/cuda.list && \
#    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/debian10/x86_64/7fa2af80.pub && \
#    apt-get update && \
#    apt-get install -y cuda-11-8 && \
#    apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置 CUDA 11.8 路径
#ENV PATH /usr/local/cuda-11.8/bin:$PATH
#ENV LD_LIBRARY_PATH /usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH

# 安装Python和pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# 创建python到python3的符号链接
RUN ln -s /usr/bin/python3 /usr/bin/python

# 安装 Python 依赖
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip3 install torch torchvision torchaudio --no-cache-dir --timeout=1000 --index-url https://download.pytorch.org/whl/cu118 # 手动安装Pytorch的GPU版本
RUN pip install -r requirements.txt

# 复制项目文件到容器中
COPY . /code/

# 预先加载模型
# 需要将load_whisper_model从utils.py中拆分,以避免调用与Django相关的库而产生报错
RUN python -c "from buildscript import load_whisper_model_during_build; load_whisper_model_during_build()"
