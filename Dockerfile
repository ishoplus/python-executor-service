# 使用一个官方的 Python 镜像作为基础
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 注意：这里安装了 Flask 和 gunicorn，如果你的 requirements.txt 中已经包含它们，可以移除后面的显式安装。
# 为了确保所有依赖都通过 requirements.txt 安装，通常只保留 `pip install -r requirements.txt`
RUN pip install --no-cache-dir -r requirements.txt

# --- 添加安装中文字体的步骤 ---
# python:3.9-slim-buster 是基于 Debian 的，所以使用 apt-get
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fontconfig \
    fonts-wqy-zenhei && \
    rm -rf /var/lib/apt/lists/*

# 更新字体缓存
RUN fc-cache -fv
# --- 字体安装结束 ---

# 复制应用程序代码
COPY app.py .

# 暴露 Flask 应用程序将监听的端口
EXPOSE 8000

# 定义容器启动时运行的命令
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]