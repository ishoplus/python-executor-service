# mcp_server_impl.py (這是一個假設性的結構，你需要根據你實際的代碼來修改)
import sys
import json
import logging
from typing import Any, Dict # <--- ADD THIS LINE!

# 配置日誌，讓錯誤訊息也輸出到 stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
server_logger = logging.getLogger(__name__)

# 假設這是你的初始化邏輯
def _handle_initialize(params: Any) -> Dict[str, Any]:
    server_logger.info("MCP server: Received initialize command.")
    try:
        # 在這裡添加你的實際初始化邏輯
        # 例如，加載配置、連接資料庫、檢查文件等

        # 假設某個操作失敗了
        # if not some_critical_resource_exists():
        #     server_logger.error("Critical resource not found during initialization!")
        #     raise Exception("Missing critical resource X")

        server_logger.info("MCP server: Initialization successful.")
        return {"status": "success"} # 成功響應
    except Exception as e:
        server_logger.exception("MCP server: Initialization failed due to an internal error.") # <--- 關鍵：使用 exception 記錄詳細堆棧
        return {"status": "error", "message": f"Internal server error during initialization: {str(e)}"} # <--- 提供更詳細的錯誤訊息

# 假設這是你的主處理函數
def process_request(request: Dict[str, Any]) -> Dict[str, Any]:
    jsonrpc_version = request.get("jsonrpc")
    method = request.get("method")
    params = request.get("params")
    req_id = request.get("id")

    if jsonrpc_version != "2.0":
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request: Missing 'jsonrpc: 2.0'"}, "id": req_id}

    response_result = {}
    error_obj = None

    try:
        if method == "initialize":
            response_result = _handle_initialize(params)
        elif method == "list_tools":
            server_logger.info("MCP server: Received list_tools command.")
            # 在這裡添加你的工具列表邏輯
            response_result = {"tools": [{"name": "example_tool", "description": "A test tool"}]}
        # ... 其他方法 (call_tool, list_resources, etc.)
        else:
            error_obj = {"code": -32601, "message": f"Method not found: {method}"}

    except Exception as e:
        server_logger.exception(f"Error processing method {method}:")
        error_obj = {"code": -32000, "message": f"Internal server error: {str(e)}"}

    if error_obj:
        return {"jsonrpc": "2.0", "error": error_obj, "id": req_id}
    else:
        return {"jsonrpc": "2.0", "result": response_result, "id": req_id}

# 主循環 (讀取 stdin, 處理請求, 寫入 stdout)
def main():
    server_logger.info("MCP server subprocess started. Ready to receive commands.")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break # stdin closed

            request_data = json.loads(line)
            response_data = process_request(request_data)

            sys.stdout.write(json.dumps(response_data) + '\n')
            sys.stdout.flush() # 確保響應被立即發送

        except json.JSONDecodeError as e:
            server_logger.error(f"MCP server: JSON Decode Error: {e}, Line: {line.strip()}", exc_info=True)
            error_response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}, "id": None}
            sys.stdout.write(json.dumps(error_response) + '\n')
            sys.stdout.flush()
        except Exception as e:
            server_logger.exception("MCP server: Unexpected error in main loop.")
            error_response = {"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Server internal error: {e}"}, "id": None}
            sys.stdout.write(json.dumps(error_response) + '\n')
            sys.stdout.flush()

if __name__ == "__main__":
    main()