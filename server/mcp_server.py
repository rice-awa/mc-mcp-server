import json
import logging
import asyncio
import inspect
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from mcp.server.fastmcp import FastMCP
from .utils.tools import tool_registry, ToolResult

logger = logging.getLogger("mc-agent-server")

class MCPServer:
    """
    MCP服务器实现，基于FastMCP。
    
    提供与外部MCP客户端通信的能力，并转发请求到Minecraft服务器。
    """
    
    def __init__(self, config, minecraft_server=None):
        """
        初始化MCP服务器。
        
        Args:
            config (dict): 服务器配置
            minecraft_server (MinecraftServer, optional): Minecraft服务器实例
        """
        self.config = config
        self.minecraft_server = minecraft_server
        self.name = config.get("agent", {}).get("name", "Minecraft Assistant")
        self.description = config.get("agent", {}).get("description", "AI助手用于Minecraft交互")
        self.version = config.get("agent", {}).get("version", "1.0.0")
        
        # 创建FastMCP服务器
        self.mcp_server = FastMCP(
            name=self.name,
            description=self.description,
            dependencies=["asyncio", "websockets", "uuid", "mcp", "python-dotenv", "fastapi", "uvicorn", "pydantic"]
        )
        
        # 设置默认的host和port
        self.mcp_server.settings.host = config.get("mcp", {}).get("host", "0.0.0.0")
        self.mcp_server.settings.port = config.get("mcp", {}).get("port", 8000)
        
        # 更新工具注册表中的服务器引用
        tool_registry.update_minecraft_server(minecraft_server)
        tool_registry.update_mcp_server(self)
        
        # 自动导入工具模块
        self._import_tool_modules()
        
        # 注册工具和资源
        self._register_tools()
        self._register_resources()
        
    def _import_tool_modules(self):
        """自动导入工具模块"""
        try:
            # 项目根目录
            import tools
            
            # 导入tools包中的所有模块
            logger.info("正在导入工具模块...")
            
            # 遍历tools包中的所有模块
            tools_path = Path(tools.__path__[0])
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if not module_info.ispkg and module_info.name != "__init__":
                    try:
                        module_name = f"tools.{module_info.name}"
                        logger.info(f"导入模块: {module_name}")
                        importlib.import_module(module_name)
                    except Exception as e:
                        logger.error(f"导入模块 {module_info.name} 时出错: {e}", exc_info=True)
            
            logger.info(f"工具模块导入完成，已注册 {len(tool_registry.get_all_tool_names())} 个工具")
            
        except ImportError as e:
            logger.warning(f"无法导入工具模块: {e}")
        except Exception as e:
            logger.error(f"导入工具模块时出错: {e}", exc_info=True)
        
    def _register_tools(self):
        """注册MCP工具"""
        
        # 注册内置基本工具（这些工具不需要复杂的实现，直接在这里定义）
        # 也可以将这些移到tools目录中使用装饰器注册
        
        @self.mcp_server.tool()
        async def execute_command(command: str, client_id: str = None, wait_response: bool = True) -> dict:
            """
            执行Minecraft命令。
            
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
            
            try:
                # 使用第一个可用的连接，如果未指定client_id
                if not client_id and self.minecraft_server.active_connections:
                    client_id = next(iter(self.minecraft_server.active_connections.keys()))
                
                if not client_id:
                    return {
                        "success": False,
                        "error": "没有活跃的Minecraft连接"
                    }
                
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
                
                # 如果不等待响应或没有收到响应
                if not wait_response or not response:
                    return {
                        "success": True,
                        "message": f"命令已执行: {command}",
                        "request_id": request_id,
                        "response": None
                    }
                
                # 返回带有响应的结果
                return {
                    "success": True,
                    "message": f"命令已执行: {command}",
                    "request_id": request_id,
                    "response": response
                }
            except Exception as e:
                logger.error(f"执行命令时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.mcp_server.tool()
        async def send_message(message: str, client_id: str = None, target: str = None, wait_response: bool = False) -> dict:
            """
            发送消息到游戏聊天。
            
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
            
            try:
                # 使用第一个可用的连接，如果未指定client_id
                if not client_id and self.minecraft_server.active_connections:
                    client_id = next(iter(self.minecraft_server.active_connections.keys()))
                
                if not client_id:
                    return {
                        "success": False,
                        "error": "没有活跃的Minecraft连接"
                    }
                
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
        
        @self.mcp_server.tool()
        async def get_tool_packages() -> dict:
            """
            获取可用的工具包列表。
            
            返回所有可用的工具扩展包及其简短描述。
            
            Returns:
                dict: 工具包信息
            """
            if self.minecraft_server and hasattr(self.minecraft_server, "agent_server"):
                agent_server = self.minecraft_server.agent_server
                if agent_server:
                    try:
                        packages = agent_server.get_tool_packages()
                        return {
                            "success": True,
                            "packages": packages
                        }
                    except Exception as e:
                        logger.error(f"获取工具包列表时出错: {e}", exc_info=True)
                        return {
                            "success": False,
                            "error": f"获取工具包列表时出错: {str(e)}"
                        }
            
            return {
                "success": False,
                "error": "Agent服务器未连接或不可用"
            }
        
        @self.mcp_server.tool()
        async def get_package_tools(package_name: str) -> dict:
            """
            获取特定工具包中的工具列表。
            
            Args:
                package_name (str): 工具包名称
                
            Returns:
                dict: 工具包中的工具信息
            """
            if self.minecraft_server and hasattr(self.minecraft_server, "agent_server"):
                agent_server = self.minecraft_server.agent_server
                if agent_server:
                    try:
                        tools = agent_server.get_package_tools(package_name)
                        return {
                            "success": True,
                            "package": package_name,
                            "tools": tools
                        }
                    except Exception as e:
                        logger.error(f"获取工具包 {package_name} 的工具列表时出错: {e}", exc_info=True)
                        return {
                            "success": False,
                            "error": f"获取工具包工具列表时出错: {str(e)}"
                        }
            
            return {
                "success": False,
                "error": "Agent服务器未连接或不可用"
            }
        
        # 自动注册工具注册表中的所有工具
        for tool_name in tool_registry.get_all_tool_names():
            self._register_tool_from_registry(tool_name)
    
    def _register_tool_from_registry(self, tool_name: str):
        """
        从工具注册表中注册工具到MCP服务器。
        
        Args:
            tool_name (str): 工具名称
        """
        # 获取工具文档
        doc_string = tool_registry.get_tool_doc(tool_name)
        if not doc_string:
            logger.warning(f"工具 {tool_name} 没有文档字符串")
            return
        
        # 动态创建工具处理函数
        @self.mcp_server.tool()
        async def dynamic_tool(**kwargs):
            """动态生成的工具处理函数"""
            # 从注册表获取工具实例
            tool = tool_registry.get_tool(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 不可用"
                }
            
            try:
                # 执行工具
                result = await tool.execute(**kwargs)
                
                # 如果结果是ToolResult实例，转换为字典
                if isinstance(result, ToolResult):
                    return result.to_dict()
                
                # 否则直接返回结果（向后兼容）
                return result
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 时出错: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # 设置函数名称和文档字符串
        dynamic_tool.__name__ = tool_name
        dynamic_tool.__doc__ = doc_string
        
        logger.info(f"已从注册表注册工具到MCP: {tool_name}")
    
    def _register_resources(self):
        """注册MCP资源"""
        
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
            
            # 实际实现中应该从游戏中获取玩家信息
            # 这里只返回模拟数据
            return {
                "name": player_name,
                "position": {"x": 0, "y": 0, "z": 0},
                "health": 20,
                "level": 0,
                "gamemode": "survival"
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
            
            # 实际实现中应该从游戏中获取世界信息
            # 这里只返回模拟数据
            return {
                "name": "Minecraft World",
                "time": 0,
                "weather": "clear",
                "difficulty": "normal",
                "gamemode": "survival"
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
            
            # 实际实现中应该从游戏中获取方块信息
            # 这里只返回模拟数据
            return {
                "position": {"x": x, "y": y, "z": z},
                "type": "unknown",
                "properties": {}
            }
    
    def run(self, transport="sse"):
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
            # 直接调用FastMCP的run方法
            self.mcp_server.run(transport="sse")
        elif transport == "stdio":
            # 使用标准输入/输出传输
            self.mcp_server.run(transport="stdio")
        else:
            raise ValueError(f"不支持的传输方式: {transport}")
    
    def update_minecraft_server(self, minecraft_server):
        """
        更新Minecraft服务器引用。
        
        Args:
            minecraft_server: 新的Minecraft服务器实例
        """
        self.minecraft_server = minecraft_server
        
        # 同时更新工具注册表中的引用
        tool_registry.update_minecraft_server(minecraft_server)
        
        logger.info("已更新MCP服务器的Minecraft服务器引用") 