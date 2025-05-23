# 使用一个官方的 Python 镜像作为基础
FROM python:3.9-slim-buster
# Keep this, or python:3.9-alpine if you prefer smaller size

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 在构建阶段安装所有依赖，包括 gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用程序代码
# IMPORTANT: Ensure app.py is directly in the WORKDIR /app
COPY app.py .
# Explicitly copy app.py
COPY . .
# Then copy other files (like any other Python files for the sandbox)

# 暴露 Flask 应用程序将监听的端口
EXPOSE 8000

# 定义容器启动时运行的命令
# 确保 Gunicorn 命令明确指向 app.py 中的 'app' 实例
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]