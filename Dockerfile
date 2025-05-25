# 使用一个官方的 Python 镜像作为基础
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制依赖文件 (如果 requirements.txt 中有 Flask 等)
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt Flask gunicorn

# 复制应用程序代码
# 这会把 app.py 复制到 /app 目录下
COPY app.py .

# 暴露 Flask 应用程序将监听的端口
EXPOSE 8000

# 定义容器启动时运行的命令
# 直接使用 Gunicorn 运行 app.py 中的 'app' 实例
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]