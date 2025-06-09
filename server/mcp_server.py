import json
import logging
import asyncio
import inspect
import importlib
import pkgutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
from mcp.server.fastmcp import FastMCP
from .utils.tools import tool_registry, ToolResult

logger = logging.getLogger("mc-agent-server")

class MCPServer:
    """
    MCP服务器实现，基于FastMCP。
    
    提供与外部MCP客户端通信的能力，并转发请求到Minecraft服务器。
    
    Attributes:
        config (dict): 服务器配置
        minecraft_server (MinecraftServer): Minecraft服务器实例
        name (str): 服务器名称
        description (str): 服务器描述
        version (str): 服务器版本
        mcp_server (FastMCP): FastMCP服务器实例
    """
    
    def __init__(self, config: dict, minecraft_server: Optional[Any] = None):
        """
        初始化MCP服务器。
        
        Args:
            config (dict): 服务器配置
            minecraft_server (MinecraftServer, optional): Minecraft服务器实例
        """
        self.config = config
        self.minecraft_server = minecraft_server
        agent_config = config.get("agent", {})
        
        self.name = agent_config.get("name", "Minecraft Assistant")
        self.description = agent_config.get("description", "AI助手用于Minecraft交互")
        self.version = agent_config.get("version", "1.0.0")
        
        # 创建线程池用于同步工具执行
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        
        # 创建FastMCP服务器
        mcp_config = config.get("mcp", {})
        self.mcp_server = FastMCP(
            name=self.name,
            description=self.description,
            dependencies=[]  # 移除硬编码依赖
        )
        
        # 配置服务器设置
        self.mcp_server.settings.host = mcp_config.get("host", "0.0.0.0")
        self.mcp_server.settings.port = mcp_config.get("port", 8000)
        
        # 更新工具注册表
        tool_registry.update_minecraft_server(minecraft_server)
        tool_registry.update_mcp_server(self)
        
        # 注册工具和资源
        self._register_tools()
        self._register_resources()
        
        # 延迟导入工具模块（在需要时导入）
        self.tools_imported = False
        
    def _import_tool_modules(self) -> None:
        """
        按需导入工具模块。
        
        该方法会导入tools包中的所有非__init__模块，用于注册可用的工具。
        """
        if self.tools_imported:
            return
            
        try:
            logger.info("开始导入工具模块...")
            import tools
            
            tools_path = Path(tools.__path__[0])
            imported_count = 0
            
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.ispkg or module_info.name == "__init__":
                    continue
                    
                try:
                    module_name = f"tools.{module_info.name}"
                    importlib.import_module(module_name)
                    logger.debug(f"成功导入工具模块: {module_name}")
                    imported_count += 1
                except Exception as e:
                    logger.error(f"导入模块 {module_info.name} 失败: {e}", exc_info=True)
            
            logger.info(f"工具模块导入完成，已导入 {imported_count} 个模块")
            self.tools_imported = True
        except ImportError:
            logger.warning("未找到工具包，跳过工具导入")
        except Exception as e:
            logger.error(f"工具导入过程中出错: {e}", exc_info=True)
            self.tools_imported = True  # 防止重复尝试导入
    
    def _get_active_client_id(self) -> Optional[str]:
        """
        获取活跃的客户端ID。
        
        如果没有指定客户端ID，则返回第一个活跃连接的客户端ID。
        
        Returns:
            Optional[str]: 客户端ID，如果没有活跃连接则返回None
        """
        if not self.minecraft_server or not self.minecraft_server.active_connections:
            return None
        return next(iter(self.minecraft_server.active_connections.keys()))
    
    def _register_builtin_tools(self) -> None:
        """注册内置工具函数"""
        
        @self.mcp_server.tool()
        async def execute_command(command: str, client_id: str = None, wait_response: bool = True) -> dict:
            """
            与Minecraft客户端交互的内置工具，优先使用,执行Minecraft命令。
            
            Args:
                command (str): 要执行的命令
                client_id (str, optional): 客户端ID
                wait_response (bool, optional): 是否等待命令响应
                
            Returns:
                dict: 命令执行结果，包含响应数据
            """
            if not self.minecraft_server:
                return {
                    "success": False,
                    "error": "Minecraft服务器未连接"
                }
            
            client_id = client_id or self._get_active_client_id()
            if not client_id:
                return {
                    "success": False,
                    "error": "没有活跃的Minecraft连接"
                }
            
            try:
                # 执行命令并等待响应
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return {
                        "success": False,
                        "error": "命令发送失败"
                    }
                
                result = {
                    "success": True,
                    "message": f"命令已执行: {command}",
                    "request_id": request_id
                }
                
                # 如果等待响应且有响应，添加响应数据
                if wait_response and response:
                    result["response"] = response
                
                return result
            except Exception as e:
                logger.error(f"执行命令时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.mcp_server.tool()
        async def send_message(message: str, client_id: str = None, target: str = None, wait_response: bool = False) -> dict:
            """
            与Minecraft客户端交互的内置工具，优先使用,发送消息到游戏聊天。
            
            Args:
                message (str): 要发送的消息
                client_id (str, optional): 客户端ID
                target (str, optional): 目标玩家，默认为所有人
                wait_response (bool, optional): 是否等待命令响应
                
            Returns:
                dict: 消息发送结果
            """
            if not self.minecraft_server:
                return {
                    "success": False,
                    "error": "Minecraft服务器未连接"
                }
            
            client_id = client_id or self._get_active_client_id()
            if not client_id:
                return {
                    "success": False,
                    "error": "没有活跃的Minecraft连接"
                }
            
            try:
                # 发送消息
                success, request_id, response = await self.minecraft_server.send_game_message(
                    client_id, 
                    message, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return {
                        "success": False,
                        "error": "消息发送失败"
                    }
                
                result = {
                    "success": True,
                    "message": message,
                    "target": target or "all",
                    "request_id": request_id
                }
                
                # 如果等待响应且有响应，添加响应数据
                if wait_response and response:
                    result["response"] = response
                
                return result
            except Exception as e:
                logger.error(f"发送消息时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def _register_tool_management_tools(self) -> None:
        """注册工具管理相关工具"""
        
        @self.mcp_server.tool()
        async def get_tool_extension_packages() -> dict:
            """
            获取可用的工具拓展包列表。
            
            返回所有可用的工具拓展包及其简短描述。这些拓展包包含了专门用于Minecraft交互的各类工具集合。
            
            Returns:
                dict: 工具拓展包信息，包含名称和描述
            """
            if not self.minecraft_server or not hasattr(self.minecraft_server, "agent_server"):
                return {
                    "success": False,
                    "error": "Agent服务器未连接或不可用"
                }
            
            try:
                packages = self.minecraft_server.agent_server.get_tool_packages()
                return {
                    "success": True,
                    "extension_packages": packages
                }
            except Exception as e:
                logger.error(f"获取工具拓展包列表时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"获取工具拓展包列表时出错: {str(e)}"
                }
        
        @self.mcp_server.tool()
        async def get_extension_package_tools(package_name: str) -> dict:
            """
            获取特定工具拓展包中的工具列表。
            
            Args:
                package_name (str): 工具拓展包名称
                
            Returns:
                dict: 工具拓展包中的工具信息，包含工具名称和描述
            """
            if not self.minecraft_server or not hasattr(self.minecraft_server, "agent_server"):
                return {
                    "success": False,
                    "error": "Agent服务器未连接或不可用"
                }
            
            try:
                tools = self.minecraft_server.agent_server.get_package_tools(package_name)
                return {
                    "success": True,
                    "package": package_name,
                    "tools": tools
                }
            except Exception as e:
                logger.error(f"获取工具拓展包 {package_name} 的工具列表时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"获取工具拓展包工具列表时出错: {str(e)}"
                }
            
        @self.mcp_server.tool()
        async def get_all_extension_tools() -> dict:
            """
            获取所有可用的工具列表。
            
            返回所有已注册的工具及其简短描述，不按拓展包分类。
            注意：使用拓展包中的工具时需要使用use_extension_tool函数，并传入工具名称和参数。
            
            Returns:
                dict: 所有可用工具的信息，包含工具名称和描述
            """
            if not self.minecraft_server or not hasattr(self.minecraft_server, "agent_server"):
                return {
                    "success": False,
                    "error": "Agent服务器未连接或不可用"
                }
            
            try:
                tools = self.minecraft_server.agent_server.get_tools()
                return {
                    "success": True,
                    "tools": tools
                }
            except Exception as e:
                logger.error(f"获取所有工具列表时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"获取所有工具列表时出错: {str(e)}"
                }
            
        @self.mcp_server.tool()
        async def use_extension_tool(tool_name: str, kwargs: Dict[str, Any] = None) -> dict:
            """
            通用工具调用接口，用于调用任何已注册的工具拓展包中的工具。
            
            Args:
                tool_name (str): 要调用的工具名称
                kwargs (dict): 工具参数字典
                
            Returns:
                dict: 工具执行结果
            """
            # 确保工具模块已导入
            self._import_tool_modules()
            
            # 从注册表获取工具实例
            tool = tool_registry.get_tool(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 不可用或未找到"
                }
            
            try:
                # 记录参数
                logger.info(f"执行工具 {tool_name} - 参数: {kwargs or {}}")
                
                # 如果没有提供参数，使用空字典
                actual_kwargs = kwargs or {}
                
                # 执行工具（支持同步和异步工具）
                if inspect.iscoroutinefunction(tool.execute):
                    result = await tool.execute(**actual_kwargs)
                else:
                    # 同步工具在线程池中执行
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(
                        self.thread_pool, 
                        lambda: tool.execute(**actual_kwargs)
                    )
                
                # 标准化返回结果
                if isinstance(result, ToolResult):
                    return result.to_dict()
                elif isinstance(result, dict):
                    return result
                else:
                    # 其他类型结果统一封装
                    return {
                        "success": True,
                        "result": result
                    }
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def _register_tools(self) -> None:
        """
        注册所有MCP工具。
        
        包括内置基本工具和工具管理工具。
        """
        # 注册内置工具
        self._register_builtin_tools()
        
        # 注册工具管理工具
        self._register_tool_management_tools()
    
    def _register_resources(self) -> None:
        """
        注册MCP资源。
        
        包括玩家信息、世界信息和方块信息等资源。
        """
        
        @self.mcp_server.resource("minecraft://player/{player_name}")
        async def get_player_info(player_name: str) -> dict:
            """
            获取玩家信息。
            
            Args:
                player_name (str): 玩家名称
                
            Returns:
                dict: 玩家信息
            """
            if not self.minecraft_server:
                return {
                    "error": "Minecraft服务器未连接"
                }
            
            try:
                # 实际实现中应该从游戏中获取玩家信息
                # 这里只返回模拟数据
                return {
                    "name": player_name,
                    "position": {"x": 0, "y": 0, "z": 0},
                    "health": 20,
                    "level": 0,
                    "gamemode": "survival"
                }
            except Exception as e:
                logger.error(f"获取玩家信息时出错: {e}", exc_info=True)
                return {
                    "error": str(e)
                }
        
        @self.mcp_server.resource("minecraft://world")
        async def get_world_info() -> dict:
            """
            获取当前世界信息。
            
            Returns:
                dict: 世界信息
            """
            if not self.minecraft_server:
                return {
                    "error": "Minecraft服务器未连接"
                }
            
            try:
                # 实际实现中应该从游戏中获取世界信息
                # 这里只返回模拟数据
                return {
                    "name": "Minecraft World",
                    "time": 0,
                    "weather": "clear",
                    "difficulty": "normal",
                    "gamemode": "survival"
                }
            except Exception as e:
                logger.error(f"获取世界信息时出错: {e}", exc_info=True)
                return {
                    "error": str(e)
                }
        
        @self.mcp_server.resource("minecraft://world/block/{x}/{y}/{z}")
        async def get_block_info(x: int, y: int, z: int) -> dict:
            """
            获取指定坐标的方块信息。
            
            Args:
                x (int): X坐标
                y (int): Y坐标
                z (int): Z坐标
                
            Returns:
                dict: 方块信息
            """
            if not self.minecraft_server:
                return {
                    "error": "Minecraft服务器未连接"
                }
            
            try:
                # 实际实现中应该从游戏中获取方块信息
                # 这里只返回模拟数据
                return {
                    "position": {"x": x, "y": y, "z": z},
                    "type": "unknown",
                    "properties": {}
                }
            except Exception as e:
                logger.error(f"获取方块信息时出错: {e}", exc_info=True)
                return {
                    "error": str(e)
                }
    
    def run(self, transport: str = "sse") -> None:
        """
        启动MCP服务器。
        
        Args:
            transport (str): 传输方式，支持"sse"和"stdio"
            
        Raises:
            ValueError: 如果传输方式不受支持
        """
        host = self.mcp_server.settings.host
        port = self.mcp_server.settings.port
        logger.info(f"启动MCP服务器，使用{transport}传输，地址: {host}:{port}")
        
        if transport == "sse":
            # 使用SSE传输
            self.mcp_server.run(transport="sse")
        elif transport == "stdio":
            # 使用标准输入/输出传输
            self.mcp_server.run(transport="stdio")
        else:
            raise ValueError(f"不支持的传输方式: {transport}")
    
    def update_minecraft_server(self, minecraft_server: Any) -> None:
        """
        更新Minecraft服务器引用。
        
        Args:
            minecraft_server: 新的Minecraft服务器实例
        """
        self.minecraft_server = minecraft_server
        
        # 同时更新工具注册表中的引用
        tool_registry.update_minecraft_server(minecraft_server)
        
        logger.info("已更新MCP服务器的Minecraft服务器引用")