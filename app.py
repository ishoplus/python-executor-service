# app.py
from flask import Flask, jsonify, request # 导入 request
import asyncio
import logging
import os
import tempfile # 导入 tempfile
import uuid # 导入 uuid
import subprocess # 导入 subprocess
import atexit # 导入 atexit 模块

from mcp_controller import mcp_bp, initialize_mcp_service_async, cleanup_mcp_service_async, get_mcp_service_async # 导入新的初始化/清理函数

logging.basicConfig(level=logging.INFO) # Basic logging configuration
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register MCP blueprint
app.register_blueprint(mcp_bp)

# --- 添加这个新的健康检查端点 ---
@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Python executor service is healthy"}), 200
# --- 结束添加 ---

# 确保在 Gunicorn 启动时（或 Flask 应用启动时）调用此函数
def run_startup_tasks():
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(initialize_mcp_service_async())
    else:
        # 如果事件循环尚未运行 (例如在某些开发环境中直接运行 app.py)
        # 则需要手动运行事件循环来执行初始化
        loop.run_until_complete(initialize_mcp_service_async())
        logger.info("McpService initialized via manual event loop run.")

# 在应用关闭时执行异步清理
def run_shutdown_tasks():
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(cleanup_mcp_service_async())
    else:
        # 如果事件循环尚未运行 (例如在某些开发环境中直接运行 app.py)
        loop.run_until_complete(cleanup_mcp_service_async())
        logger.info("McpService cleaned up via manual event loop run.")

# 注册清理函数，确保在应用退出时调用
atexit.register(run_shutdown_tasks)

@app.route('/execute-python', methods=['POST'])
def execute_python_code():
    data = request.get_json()
    python_code = data.get('code')

    if not python_code:
        return jsonify({"error": "No Python code provided"}), 400

    # Create a unique temporary file to store the Python code
    # This helps with isolation between different requests
    temp_dir = tempfile.gettempdir()
    unique_filename = f"script_{uuid.uuid4().hex}.py"
    script_path = os.path.join(temp_dir, unique_filename)

    try:
        # Write the Python code to the temporary file
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        # Execute the Python script using subprocess
        # Using python3 ensures the correct interpreter if both python and python3 exist
        process = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True, # Capture output as text (UTF-8)
            timeout=30 # Set a timeout for script execution (e.g., 30 seconds)
        )

        stdout = process.stdout
        stderr = process.stderr
        exit_code = process.returncode

        # Clean up the temporary file
        os.remove(script_path)

        return jsonify({
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        })

    except subprocess.TimeoutExpired:
        # If the script times out, ensure the process is killed
        process.kill()
        os.remove(script_path)
        return jsonify({"error": "Python script execution timed out"}), 408
    except Exception as e:
        # General error handling
        if os.path.exists(script_path):
            os.remove(script_path) # Clean up even on general error
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # Listen on all interfaces (0.0.0.0) and port 8000
    # Railway will expose this port
    app.run(host='0.0.0.0', port=8000)
