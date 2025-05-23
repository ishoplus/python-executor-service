from flask import Flask, jsonify, request
import asyncio
import logging
import os
import tempfile
import uuid
import subprocess
# import atexit # 不再需要直接导入 atexit，因为清理由 Gunicorn 钩子处理

from mcp_controller import mcp_bp, initialize_mcp_service_async, cleanup_mcp_service_async, get_mcp_service_async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register MCP blueprint
app.register_blueprint(mcp_bp)

# 健康检查端点
@app.route('/healthz', methods=['GET'])
def health_check():
    # 可以在这里添加更复杂的健康检查逻辑，例如检查 MCP 服务是否已初始化
    # 但对于基本的健康检查，返回 200 OK 就足够了
    return jsonify({"status": "ok", "message": "Python executor service is healthy"}), 200

# --- 移除以下代码，因为它们现在由 gunicorn_config.py 中的钩子处理 ---
# def run_startup_tasks():
#     loop = asyncio.get_event_loop()
#     if loop.is_running():
#         loop.create_task(initialize_mcp_service_async())
#     else:
#         loop.run_until_complete(initialize_mcp_service_async())
#         logger.info("McpService initialized via manual event loop run.")

# def run_shutdown_tasks():
#     loop = asyncio.get_event_loop()
#     if loop.is_running():
#         loop.create_task(cleanup_mcp_service_async())
#     else:
#         loop.run_until_complete(cleanup_mcp_service_async())
#         logger.info("McpService cleaned up via manual event loop run.")

# atexit.register(run_shutdown_tasks)
# --- 结束移除 ---

@app.route('/execute-python', methods=['POST'])
def execute_python_code():
    data = request.get_json()
    python_code = data.get('code')

    if not python_code:
        return jsonify({"error": "No Python code provided"}), 400

    temp_dir = tempfile.gettempdir()
    unique_filename = f"script_{uuid.uuid4().hex}.py"
    script_path = os.path.join(temp_dir, unique_filename)

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        process = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        stdout = process.stdout
        stderr = process.stderr
        exit_code = process.returncode

        os.remove(script_path)

        return jsonify({
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code
        })

    except subprocess.TimeoutExpired:
        process.kill()
        os.remove(script_path)
        return jsonify({"error": "Python script execution timed out"}), 408
    except Exception as e:
        if os.path.exists(script_path):
            os.remove(script_path)
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # 在 Gunicorn 环境下，这个块不会被执行
    # 如果您需要在本地直接运行 app.py 进行开发测试，
    # 可以考虑在这里手动调用 initialize_mcp_service_async()
    # 但请注意，这与 Gunicorn 的异步 worker 行为可能不同。
    app.run(host='0.0.0.0', port=8000)
