# 使用一个官方的 Python 镜像作为基础
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装依赖
COPY requirements.txt .

# 在构建阶段安装所有依赖，包括 gunicorn
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用程序代码
COPY . .

# 暴露 Flask 应用程序将监听的端口
EXPOSE 8000

# 定义容器启动时运行的命令
# 使用 gunicorn 这样的生产级 WSGI 服务器来运行 Flask 应用
# gunicorn 是一个更健壮、性能更好的选择，而非 Flask 内置的开发服务器
# 如果您不想引入 gunicorn，可以直接用 `CMD ["python3", "app.py"]`，但生产环境不推荐
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
