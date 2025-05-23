# gunicorn_config.py
import asyncio
import logging
import os

# 从 app.py 或 mcp_controller.py 导入初始化和清理函数
# 假设 initialize_mcp_service_async 和 cleanup_mcp_service_async 在 mcp_controller 中
from mcp_controller import initialize_mcp_service_async, cleanup_mcp_service_async

print("--- DEBUG: gunicorn_config.py is being loaded! ---") # Add this line
logger = logging.getLogger(__name__)

# Gunicorn 配置
worker_class = 'gevent'  # 使用 gevent 异步 worker
bind = '0.0.0.0:8000'    # 监听所有接口的 8000 端口
workers = 1              # 通常在容器环境中，一个 worker 就足够，或者根据需要调整
timeout = 30             # worker 处理请求的超时时间（秒）
# loglevel = 'info'      # Gunicorn 日志级别

# Gunicorn 钩子：在每个 worker 进程启动时执行
def on_worker_boot(worker):
#     print("--- DEBUG: on_worker_boot entered! ---") # Add this line
#     logger.info("Gunicorn worker booted, starting MCP service initialization...")
#     loop = asyncio.get_event_loop()
#     if loop.is_running():
#         # 如果事件循环已经运行 (例如 gevent 自动创建的)
#         loop.create_task(initialize_mcp_service_async())
#     else:
#         # 如果事件循环尚未运行 (在某些非标准场景下，但 gevent 通常会启动循环)
#         # 需谨慎使用 run_until_complete，因为它会阻塞当前线程直到任务完成
#         loop.run_until_complete(initialize_mcp_service_async())
#         print("--- DEBUG: on_worker_boot finished! ---") # Add this line
#         logger.info("McpService initialized in Gunicorn worker.")

# Gunicorn 钩子：在每个 worker 进程退出时执行
def on_worker_exit(worker, sig):
    logger.info(f"Gunicorn worker exiting (pid: {worker.pid}, signal: {sig}), starting MCP service cleanup...")
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(cleanup_mcp_service_async())
    else:
        loop.run_until_complete(cleanup_mcp_service_async())
    logger.info("McpService cleaned up in Gunicorn worker.")

# 如果您希望在主进程退出时进行清理（例如，当所有 worker 都退出后）
# def on_exit(server):
#     logger.info("Gunicorn master process exiting. Performing final cleanup if necessary.")
#     # 这里可以放置一些全局的、非 worker 相关的清理逻辑
