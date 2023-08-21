# 使用官方的 Python 镜像作为基础镜像
FROM python:3.10-slim

# 设置环境变量，确保 Python 输出直接到终端，不使用任何缓冲
ENV PYTHONUNBUFFERED 1

# 创建目录并设置工作目录
RUN mkdir /code
WORKDIR /code

# 安装系统级依赖
RUN apt-get update && \
    apt-get install -y \
    gcc \
    build-essential \
    libmariadb-dev-compat \
    libmariadb-dev \
    libssl-dev \
    pkg-config \
    ffmpeg && \
    apt-get clean

# 安装CUDA 11.8
RUN apt-get install -y gnupg2 && \
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/debian10/x86_64/ /" | tee /etc/apt/sources.list.d/cuda.list && \
    apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/debian10/x86_64/7fa2af80.pub && \
    apt-get update && \
    apt-get install -y cuda-11-8 && \
    apt-get clean

# 设置 CUDA 11.8 路径
ENV PATH /usr/local/cuda-11.8/bin:$PATH
ENV LD_LIBRARY_PATH /usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH

# 安装 Python 依赖
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip3 install torch torchvision torchaudio --no-cache-dir --index-url https://download.pytorch.org/whl/cu118 # 手动安装Pytorch的GPU版本
RUN pip install -r requirements.txt

# 复制项目文件到容器中
COPY . /code/
