# 使用一个官方的 Python 镜像作为基础
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# --- 新增步骤：安装系统级构建依赖 ---
# 更新 apt 包列表并安装必要的编译工具和 Python 开发头文件
# build-essential 包含了 gcc 等编译工具
# python3-dev 包含了 Python 的开发头文件，用于编译依赖 C 扩展的 Python 包
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev && \
    # 清理 apt 缓存以减小镜像大小
    rm -rf /var/lib/apt/lists/*

# 在构建阶段安装所有 Python 依赖，包括 gunicorn 和 aiofiles
# (asyncio 是 Python 内置的，但一些额外的库如 aiofiles 可能需要)
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
COPY app.py .
COPY mcp_controller.py .
COPY mcp_service.py .
COPY mcp_stdio_client.py .
COPY mcp_script_manager.py .
COPY mcp_server_impl.py .
COPY gunicorn_config.py .
# <-- 确保 gunicorn_config.py 被复制

# 设置 MCP 服务器脚本的路径 (在容器内部)
ENV MCP_SERVER_SCRIPT="/app/mcp_server_impl.py"
ENV MCP_SERVER_COMMAND="python3"

# 暴露 Flask 应用程序将监听的端口
EXPOSE 8000

# 定义容器启动时运行的命令，使用 gunicorn_config.py 配置文件
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]