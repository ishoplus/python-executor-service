# app.py
from flask import Flask, request, jsonify
import subprocess
import os
import tempfile
import uuid
import logging # <-- 新增：导入 logging 模块

# <-- 新增：配置基本的日志输出到控制台，以便在容器日志中看到
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
logger.info("Flask app instance created.") # <-- 新增：应用程序实例创建时的日志

# --- 添加这个新的健康检查端点 ---
@app.route('/healthz', methods=['GET'])
def health_check():
    logger.info("Health check endpoint hit!") # <-- 新增：健康检查被访问时的日志
    return jsonify({"status": "ok", "message": "Python executor service is healthy"}), 200
# --- 结束添加 ---

@app.route('/execute-python', methods=['POST'])
def execute_python_code():
    logger.info("Execute Python code endpoint hit!") # <-- 新增：执行代码端点被访问时的日志
    data = request.get_json()
    python_code = data.get('code')

    if not python_code:
        logger.warning("No Python code provided in request.") # <-- 新增：警告日志
        return jsonify({"error": "No Python code provided"}), 400

    # ... 其他代码保持不变 ...
    # 为 subprocess.run 添加 try/except 块内部的日志，特别是如果它经常被调用
    try:
        process = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True, # Capture output as text (UTF-8)
            timeout=30 # Set a timeout for script execution (e.g., 30 seconds)
        )
        logger.info(f"Python script execution finished with exit code: {process.returncode}") # <-- 新增
        # ...
    except subprocess.TimeoutExpired:
        logger.error("Python script execution timed out!") # <-- 新增
        # ...
    except Exception as e:
        logger.exception("An error occurred during script execution.") # <-- 新增
        # ...

if __name__ == '__main__':
    # ... 保持不变 ...
    app.run(host='0.0.0.0', port=8000)