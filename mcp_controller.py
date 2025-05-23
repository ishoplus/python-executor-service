from flask import Blueprint, jsonify, request
import time
import asyncio
import logging
from typing import Optional
from asgiref.sync import AsyncToSync # 导入 AsyncToSync

from mcp_service import McpService
from mcp_stdio_client import McpStdioClient
from mcp_script_manager import McpScriptManager

print("--- DEBUG: mcp_controller.py is being loaded! ---") # Add this line
logger = logging.getLogger(__name__)

mcp_bp = Blueprint('mcp_api', __name__, url_prefix='/api/mcp')

_mcp_service: Optional[McpService] = None
# <--- MODIFIED: Add asyncio.Lock for thread-safe initialization --->
_mcp_service_lock = asyncio.Lock()

# 辅助函数：获取已初始化的 McpService 实例 (同步版本，谨慎使用)
def get_initialized_mcp_service_sync() -> Optional[McpService]:
    """
    Returns the currently initialized McpService instance.
    This is a synchronous getter, assuming initialization has already completed.
    Should only be used if you are absolutely sure the service is initialized.
    """
    global _mcp_service
    if _mcp_service is None:
        logger.warning("Attempted to get McpService synchronously before it was initialized. This might indicate a race condition or incorrect usage.")
    return _mcp_service

# <--- MODIFIED: get_mcp_service_async now handles full initialization with a lock --->
async def get_mcp_service_async() -> McpService:
    global _mcp_service
    # 使用 asyncio.Lock 来确保在初始化过程中只有一个协程能进行
    async with _mcp_service_lock:
        if _mcp_service is None:
            logger.error("McpService not initialized before first request. Attempting lazy async init.")
            try:
                # 实例化 McpStdioClient 和 McpScriptManager
                # 确保它们在异步上下文中被创建
                stdio_client = McpStdioClient()
                script_manager = McpScriptManager()
                _mcp_service = McpService(stdio_client, script_manager)

                # 调用 McpService 的初始化方法
                await _mcp_service.initialize()
                logger.info("McpService asynchronous initialization complete.")
            except Exception as e:
                logger.exception("McpService failed to initialize asynchronously.")
                _mcp_service = None # 初始化失败，重置服务实例
                raise RuntimeError(f"McpService failed to initialize: {e}")
        return _mcp_service

# --- Function to initialize McpService (called from app.py) ---
# <--- MODIFIED: This function is now also protected by the lock and calls the same init logic --->
async def initialize_mcp_service_async():
    print("DEBUG: initialize_mcp_service_async START") # Add this
    """
    Initializes the global McpService instance.
    This function is primarily for internal use or explicit startup.
    Consider using get_mcp_service_async() for lazy initialization.
    """
    global _mcp_service
    async with _mcp_service_lock: # 确保初始化过程是唯一的
        if _mcp_service is None:
            print("DEBUG: initialize_mcp_service_async Part 1 Done") # Add this
            logger.info("Explicitly initializing McpService asynchronously...")
            stdio_client = McpStdioClient()
            script_manager = McpScriptManager()
            _mcp_service = McpService(stdio_client, script_manager)
            await _mcp_service.initialize()
                print("DEBUG: initialize_mcp_service_async END") # Add this
            logger.info("McpService asynchronous initialization complete.")
        return _mcp_service


# --- Function to cleanup McpService (called from app.py) ---
async def cleanup_mcp_service_async():
    global _mcp_service
    if _mcp_service:
        logger.info("Cleaning up McpService asynchronously...")
        await _mcp_service.cleanup()
        _mcp_service = None
        logger.info("McpService asynchronous cleanup complete.")

# --- MCP API Routes Definition ---

@mcp_bp.route('/status', methods=['GET'])
async def get_mcp_status():
    try:
        service = await get_mcp_service_async()
        status = {
            "connected": service.is_connected(),
            "timestamp": int(time.time() * 1000)
        }
        return jsonify(status), 200
    except Exception as e:
        logger.exception("Error getting MCP status:")
        return jsonify({"error": f"Failed to retrieve status: {str(e)}"}), 500


@mcp_bp.route('/tools', methods=['GET'])
async def get_mcp_tools():
    """
    Retrieves a list of available tools from the MCP service.
    """
    try:
        service = await get_mcp_service_async()
        if service is None:
            logger.error("MCP service is not available after lazy init attempt.")
            return jsonify({"error": "MCP service not available"}), 503

        tools = await service.get_available_tools()
        return jsonify({"tools": tools}), 200
    except Exception as e:
        logger.exception("Error getting MCP tools:")
        return jsonify({"error": str(e)}), 500

@mcp_bp.route('/tools/<string:tool_name>/execute', methods=['POST'])
async def execute_mcp_tool(tool_name):
    service = await get_mcp_service_async()
    if not service.is_connected():
       return jsonify({"success": False, "error": "MCP service not connected or initialized"}), 503

    arguments = request.get_json(silent=True)
    try:
        result = await service.execute_tool(tool_name, arguments if arguments else {})
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to execute tool: {str(e)}"}), 500

@mcp_bp.route('/resources', methods=['GET'])
async def get_mcp_resources():
    service = await get_mcp_service_async()
    try:
        resources = await service.get_available_resources()
        return jsonify(resources), 200
    except Exception as e:
        logger.error("Error in /api/mcp/resources", exc_info=True)
        return jsonify({"error": f"Failed to retrieve resources: {str(e)}"}), 500

@mcp_bp.route('/resources/read', methods=['GET'])
async def read_mcp_resource():
    service = await get_mcp_service_async()
    if not service.is_connected():
        return jsonify({"success": False, "error": "MCP service not connected or initialized"}), 503

    uri = request.args.get('uri')
    if not uri:
        return jsonify({"success": False, "error": "URI parameter is required"}), 400

    try:
        content = await service.read_resource(uri)
        if content.get("success"):
            return jsonify(content), 200
        else:
            return jsonify(content), 400
    except Exception as e:
        logger.error(f"Error reading resource {uri}", exc_info=True)
        return jsonify({"success": False, "error": f"Failed to read resource: {str(e)}"}), 500

@mcp_bp.route('/prompts', methods=['GET'])
async def get_mcp_prompts():
    service = await get_mcp_service_async()
    try:
        prompts = await service.get_available_prompts()
        return jsonify(prompts), 200
    except Exception as e:
        logger.error("Error in /api/mcp/prompts", exc_info=True)
        return jsonify({"error": f"Failed to retrieve prompts: {str(e)}"}), 500
