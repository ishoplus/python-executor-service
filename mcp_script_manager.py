# mcp_script_manager.py

import os
import logging

logger = logging.getLogger(__name__)

class McpScriptManager:
    def __init__(self):
        pass # 通常不需要在这里设置基准目录，在 extract_script 中动态获取更灵活

    def extract_script(self, resource_script_name: str) -> str:
        # 1. 提取文件名，忽略传入路径中的目录部分（例如 /app/）
        script_filename = os.path.basename(resource_script_name)

        # 2. 尝试在当前工作目录查找（通常是运行 app.py 的目录）
        current_working_dir = os.getcwd()
        candidate_path_cwd = os.path.join(current_working_dir, script_filename)

        # 3. 尝试在 mcp_script_manager.py 文件所在的目录查找
        #    这通常是项目中的一个子目录，如果 mcp_server_impl.py 不在那里，可以跳过此步骤
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_path_self_dir = os.path.join(current_script_dir, script_filename)

        # 4. 尝试在项目根目录查找 (假设 mcp_script_manager.py 在项目根目录的子目录中)
        #    例如，如果 mcp_script_manager.py 在 project_root/src/
        #    那么 project_root_dir = os.path.abspath(os.path.join(current_script_dir, '..', '..'))
        #    这里我们假设 mcp_server_impl.py 在项目根目录，也就是 app.py 所在的目录
        project_root_dir = os.path.dirname(os.path.abspath(os.sys.argv[0])) # 获取主脚本 (app.py) 所在的目录
        candidate_path_project_root = os.path.join(project_root_dir, script_filename)


        possible_paths = [
            candidate_path_project_root, # 最可能的位置：与 app.py 同目录
            candidate_path_cwd,          # 其次可能：当前运行命令的目录
            candidate_path_self_dir      # 如果 mcp_server_impl.py 和 mcp_script_manager.py 在一起
        ]

        for path in possible_paths:
            logger.debug(f"Checking for script at: {path}")
            if os.path.exists(path):
                logger.info(f"Found MCP server script at: {path}")
                return path

        # 如果所有尝试都失败
        raise FileNotFoundError(f"MCP server script not found for '{resource_script_name}'. "
                                f"Tried locations: {', '.join(possible_paths)}")

# ... 其他方法

    def cleanup(self):
        """Cleans up any extracted temporary script files."""
        # For scripts directly in /app, no cleanup is needed unless they were truly temporary.
        # If you were extracting from a JAR or a complex resource, this would delete the temp copy.
        if self._extracted_script_path and os.path.exists(self._extracted_script_path):
            # Example for truly temporary files:
            # if self._extracted_script_path.startswith(tempfile.gettempdir()):
            #     os.remove(self._extracted_script_path)
            #     logger.info(f"Cleaned up temporary MCP script: {self._extracted_script_path}")
            pass # No action for directly copied files in /app