import asyncio
import logging
import subprocess
import json
import itertools
import threading # <--- NEW: For running loop in a separate thread
from typing import List, Dict, Any, Optional, Tuple, Callable, Coroutine

logger = logging.getLogger(__name__)

class McpStdioClient:
    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._is_initialized = False
        self._request_id_counter = itertools.count(1)

        # <--- NEW: Dedicated asyncio loop and thread for subprocess I/O --->
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._loop_ready_event = threading.Event() # To signal when the loop is running

    async def _run_coroutine_on_loop(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Helper to run a coroutine on the dedicated event loop."""
        if not self._loop_thread or not self._loop_thread.is_alive():
            raise RuntimeError("Dedicated asyncio loop is not running.")

        # Wait until the loop is actually ready to accept tasks
        self._loop_ready_event.wait(timeout=10) # Wait up to 10 seconds for loop to start
        if not self._loop_ready_event.is_set():
            raise RuntimeError("Dedicated asyncio loop did not become ready in time.")

        # Schedule the coroutine on the dedicated loop from the current thread
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return await asyncio.wrap_future(future) # Wrap in a local future to await in current loop


    def _run_loop_in_thread(self):
        """Method to run the asyncio loop in a separate thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        logger.info(f"Dedicated asyncio loop started in thread: {threading.current_thread().name}")
        self._loop_ready_event.set() # Signal that the loop is ready
        try:
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Dedicated asyncio loop encountered an error: {e}", exc_info=True)
        finally:
            self._loop.close()
            logger.info(f"Dedicated asyncio loop closed in thread: {threading.current_thread().name}")


    async def connect(self, command: List[str], script_path: str, *args):
        full_command = command + [script_path] + list(args)
        logger.info(f"Connecting to MCP server with command: {full_command}")

        # Start the dedicated loop thread if not already running
        if not self._loop_thread or not self._loop_thread.is_alive():
            self._loop_thread = threading.Thread(target=self._run_loop_in_thread, daemon=True, name="McpStdioClientLoop")
            self._loop_thread.start()
            logger.info("Started dedicated asyncio loop thread.")

        # Now, create the subprocess within the context of the dedicated loop
        # This ensures _process.stdout/_process.stdin are bound to _loop
        async def _internal_connect():
            try:
                self._process = await asyncio.create_subprocess_exec(
                    *full_command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logger.info("MCP server subprocess started successfully on dedicated loop.")
                # No need to return reader/writer here, they are stored on self._process
            except FileNotFoundError as e:
                logger.error(f"Command '{command[0]}' not found. Ensure Python interpreter or script is in PATH. Error: {e}")
                raise RuntimeError(f"Failed to start MCP server subprocess: {e}")
            except Exception as e:
                logger.error(f"Error starting MCP server subprocess: {e}", exc_info=True)
                raise RuntimeError(f"Failed to start MCP server subprocess: {e}")

        await self._run_coroutine_on_loop(_internal_connect())


    async def initialize(self):
        """Sends an 'initialize' command to the MCP server subprocess."""
        if not self._process or self._process.stdin is None:
            raise RuntimeError("MCP server connection not established for initialization.")

        logger.info("Sending 'initialize' command to MCP server.")
        response = await self.send_and_receive(self._create_rpc_request("initialize"))

        if response.get("result", {}).get("status") == "success":
            self._is_initialized = True
            logger.info("MCP server reported successful initialization.")
        else:
            error_info = response.get("error", {})
            error_message = error_info.get("message", "Unknown error during server initialization.")
            error_code = error_info.get("code", "N/A")
            logger.error(f"MCP server initialization failed: Code {error_code}, Message: {error_message}")
            raise RuntimeError(f"MCP server failed to initialize: Code {error_code}, Message: {error_message}")


    def _create_rpc_request(self, method: str, params: Optional[Any] = None) -> Dict[str, Any]:
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": next(self._request_id_counter)
        }
        if params is not None:
            request["params"] = params
        return request

    # send_and_receive no longer takes reader and writer as arguments
    async def send_and_receive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._process is None or self._process.returncode is not None:
            raise RuntimeError("MCP server process terminated or not started.")

        async def _internal_send_receive():
            try:
                message = json.dumps(data) + '\n'
                self._process.stdin.write(message.encode('utf-8'))
                await self._process.stdin.drain()
                logger.debug(f"Sent to MCP server: {message.strip()}")

                response_line = await self._process.stdout.readline()
                if not response_line:
                    stderr_output = await self._run_coroutine_on_loop(self._internal_get_error_output()) # Get stderr on dedicated loop
                    if self._process.returncode is not None:
                        raise EOFError(f"MCP server process terminated unexpectedly with code {self._process.returncode}. Stderr: {stderr_output.strip()}")
                    else:
                        raise EOFError(f"MCP server closed connection unexpectedly. Stderr: {stderr_output.strip()}")

                response_data = json.loads(response_line.decode('utf-8'))
                logger.debug(f"Received from MCP server: {response_data}")

                if "error" in response_data:
                    error = response_data["error"]
                    logger.error(f"Received RPC error from MCP server: Code {error.get('code')}, Message: {error.get('message')}, Data: {error.get('data')}")
                    raise RuntimeError(f"MCP server RPC error: {error.get('message', 'Unknown RPC error')}")

                return response_data
            except json.JSONDecodeError as e:
                error_output = await self._run_coroutine_on_loop(self._internal_get_error_output())
                logger.error(f"JSON decode error: {e}. Raw response: '{response_line.decode('utf-8').strip()}'. Stderr: '{error_output.strip()}'")
                raise RuntimeError(f"Invalid JSON response from MCP server: {e}. Stderr: {error_output.strip()}")
            except Exception as e:
                logger.error(f"Error during internal send/receive with MCP server: {e}", exc_info=True)
                raise

        return await self._run_coroutine_on_loop(_internal_send_receive())

    # --- Communication methods now call send_and_receive directly ---

    async def list_tools(self) -> Dict[str, Any]:
        rpc_response = await self.send_and_receive(self._create_rpc_request("list_tools"))
        return rpc_response.get("result", {})

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        params = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        rpc_response = await self.send_and_receive(self._create_rpc_request("call_tool", params))
        return rpc_response.get("result", {})

    async def list_resources(self) -> Dict[str, Any]:
        rpc_response = await self.send_and_receive(self._create_rpc_request("list_resources"))
        return rpc_response.get("result", {})

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        params = {"uri": uri}
        rpc_response = await self.send_and_receive(self._create_rpc_request("read_resource", params))
        return rpc_response.get("result", {})

    async def list_prompts(self) -> Dict[str, Any]:
        rpc_response = await self.send_and_receive(self._create_rpc_request("list_prompts"))
        return rpc_response.get("result", {})

    # --- Existing methods, disconnect needs to close the streams and stop the loop ---

    async def disconnect(self):
        if self._process:
            logger.info("Disconnecting from MCP server.")
            # Close streams if they are still open
            if self._process.stdin:
                self._process.stdin.close()
                # No need to await wait_closed() here, as it's part of the internal loop's shutdown

            async def _internal_disconnect_wait():
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5)
                    logger.info(f"MCP server process exited with code: {self._process.returncode}")
                except asyncio.TimeoutError:
                    logger.warning("MCP server process did not exit within timeout, killing it.")
                    self._process.kill()
                    await self._process.wait()
                except Exception as e:
                    logger.error(f"Error while waiting for subprocess to exit: {e}")

            # Run disconnect logic on the dedicated loop
            await self._run_coroutine_on_loop(_internal_disconnect_wait())

            self._process = None
            self._is_initialized = False

        # <--- NEW: Stop the dedicated event loop and its thread --->
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            # Give the thread a moment to stop gracefully
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=5)
                if self._loop_thread.is_alive():
                    logger.warning("Dedicated loop thread did not stop gracefully.")
        self._loop = None
        self._loop_thread = None
        self._loop_ready_event.clear() # Reset for next connection


    def is_connected(self) -> bool:
        """Checks if the subprocess is running."""
        return self._process is not None and self._process.returncode is None

    def is_initialized(self) -> bool:
        """Checks if the client itself has sent the initial handshake/command."""
        return self._is_initialized

    async def _internal_get_error_output(self) -> str:
        """Reads any pending error output from stderr (to be run on dedicated loop)."""
        if self._process and self._process.stderr:
            try:
                error_bytes = await asyncio.wait_for(self._process.stderr.read(), timeout=0.1)
                return error_bytes.decode('utf-8', errors='ignore')
            except asyncio.TimeoutError:
                return ""
            except Exception as e:
                logger.error(f"Failed to read error output from subprocess: {e}")
                return f"Failed to read error output: {e}"
        return ""

    async def get_error_output(self) -> str:
        """Public method to get error output (runs on dedicated loop)."""
        if not self._process:
            return ""
        return await self._run_coroutine_on_loop(self._internal_get_error_output())

