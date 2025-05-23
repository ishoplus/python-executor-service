import asyncio
import logging
from typing import List, Dict, Any, Optional
import os
import aiofiles # For async file operations if needed
import json # You need this for json.dumps in _parse_tools_response and _parse_tool_result

from mcp_stdio_client import McpStdioClient
from mcp_script_manager import McpScriptManager

logger = logging.getLogger(__name__)

# DTOs (simple dicts for now, consider Pydantic for larger projects)
ToolInfo = Dict[str, Any]
ToolResult = Dict[str, Any]
ResourceInfo = Dict[str, Any]
ResourceContent = Dict[str, Any]
PromptInfo = Dict[str, Any]

class McpService:
    def __init__(self, mcp_client: McpStdioClient, script_manager: McpScriptManager):
        self._mcp_client = mcp_client
        self._script_manager = script_manager
        self._initialized_event = asyncio.Event()
        server_command_str = os.getenv("MCP_SERVER_COMMAND", "python3")
        self._server_command = [server_command_str]
        self._server_script = os.getenv("MCP_SERVER_SCRIPT", "/app/mcp_server_impl.py")
        self._resource_script = os.getenv("MCP_SERVER_RESOURCE_SCRIPT", self._server_script)
        self._server_args = []

        # Store the reader and writer for the persistent connection
        # <--- REMOVED: self._reader and self._writer are now managed internally by McpStdioClient --->
        # self._reader: Optional[asyncio.StreamReader] = None
        # self._writer: Optional[asyncio.StreamWriter] = None

    async def initialize(self):
        """Initializes the MCP service."""
        try:
            actual_script_path = self._script_manager.extract_script(self._resource_script)

            # Connect method no longer returns reader/writer, it manages the subprocess internally
            await self._mcp_client.connect(self._server_command, actual_script_path, *self._server_args)

            # Pass reader/writer to client's initialize method
            # <--- MODIFIED: No longer pass reader/writer to initialize --->
            await self._mcp_client.initialize()
            self._initialized_event.set()
            logger.info("MCP service connection and initialization complete.")
        except Exception as e:
            logger.error("MCP service initialization failed", exc_info=True)
            raise RuntimeError(f"MCP service initialization failed: {e}")

    async def get_available_tools(self) -> List[ToolInfo]:
        await self._wait_for_initialization()
        try:
            # Pass reader/writer to the client method
            # <--- MODIFIED: No longer pass reader/writer to list_tools --->
            response = await self._mcp_client.list_tools()
            return self._parse_tools_response(response)
        except Exception:
            logger.error("Failed to get tool list", exc_info=True)
            return []

    def _parse_tools_response(self, response: dict) -> List[ToolInfo]:
        tools = []
        if response.get("tools") and isinstance(response["tools"], list):
            for tool_node in response["tools"]:
                tool = {
                    "name": tool_node.get("name"),
                    "description": tool_node.get("description", ""),
                    "inputSchema": json.dumps(tool_node.get("inputSchema")) if tool_node.get("inputSchema") else None
                }
                tools.append(tool)
        return tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        await self._wait_for_initialization()
        try:
            # Pass reader/writer
            # <--- MODIFIED: No longer pass reader/writer to call_tool --->
            response = await self._mcp_client.call_tool(tool_name, arguments)
            return self._parse_tool_result(response)
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _parse_tool_result(self, response: dict) -> ToolResult:
        result = {"success": True}

        if response.get("content") and isinstance(response["content"], list) and len(response["content"]) > 0:
            first_content = response["content"][0]
            if first_content.get("text"):
                result["textContent"] = first_content["text"]
            if first_content.get("type"):
                result["contentType"] = first_content["type"]

        result["rawResponse"] = json.dumps(response)
        return result

    async def get_available_resources(self) -> List[ResourceInfo]:
        await self._wait_for_initialization()
        try:
            # Pass reader/writer
            # <--- MODIFIED: No longer pass reader/writer to list_resources --->
            response = await self._mcp_client.list_resources()
            return self._parse_resources_response(response)
        except Exception:
            logger.error("Failed to get resource list", exc_info=True)
            return []

    def _parse_resources_response(self, response: dict) -> List[ResourceInfo]:
        resources = []
        if response.get("resources") and isinstance(response["resources"], list):
            for resource_node in response["resources"]:
                resource = {
                    "uri": resource_node.get("uri"),
                    "name": resource_node.get("name", ""),
                    "description": resource_node.get("description", ""),
                    "mimeType": resource_node.get("mimeType", "")
                }
                resources.append(resource)
        return resources

    async def read_resource(self, uri: str) -> ResourceContent:
        await self._wait_for_initialization()
        try:
            # Pass reader/writer
            # <--- MODIFIED: No longer pass reader/writer to read_resource --->
            response = await self._mcp_client.read_resource(uri)
            return self._parse_resource_content(response)
        except Exception as e:
            logger.error(f"Failed to read resource {uri}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _parse_resource_content(self, response: dict) -> ResourceContent:
        content = {"success": True}

        if response.get("contents") and isinstance(response["contents"], list) and len(response["contents"]) > 0:
            first_content = response["contents"][0]
            if first_content.get("text"):
                content["textContent"] = first_content["text"]
            if first_content.get("uri"):
                content["uri"] = first_content["uri"]
            if first_content.get("mimeType"):
                content["mimeType"] = first_content["mimeType"]

        content["rawResponse"] = json.dumps(response)
        return content

    async def get_available_prompts(self) -> List[PromptInfo]:
        await self._wait_for_initialization()
        try:
            # Pass reader/writer
            # <--- MODIFIED: No longer pass reader/writer to list_prompts --->
            response = await self._mcp_client.list_prompts()
            return self._parse_prompts_response(response)
        except Exception:
            logger.error("Failed to get prompt list", exc_info=True)
            return []

    def _parse_prompts_response(self, response: dict) -> List[PromptInfo]:
        prompts = []
        if response.get("prompts") and isinstance(response["prompts"], list):
            for prompt_node in response["prompts"]:
                prompt = {
                    "name": prompt_node.get("name"),
                    "description": prompt_node.get("description", ""),
                    "arguments": [arg.get("name") for arg in prompt_node.get("arguments", []) if isinstance(arg, dict)]
                }
                prompts.append(prompt)
        return prompts

    def is_connected(self) -> bool:
        """Checks if the MCP client is initialized and connected."""
        return self._mcp_client.is_connected()

    async def _wait_for_initialization(self):
        """Waits for the MCP service to be initialized."""
        if not self.is_connected():
            logger.warning("MCP service not yet initialized. Waiting...")
            await self._initialized_event.wait()
            logger.info("MCP service initialized.")

    async def cleanup(self):
        """Performs cleanup (disconnects client, cleans scripts)."""
        await self._mcp_client.disconnect() # Disconnect will handle closing streams
        self._script_manager.cleanup()
        logger.info("MCP service cleaned up.")
