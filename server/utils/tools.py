import logging
import inspect
from typing import Dict, Any, Optional, Callable, List, Type, TypeVar, Generic, Union
import functools
import asyncio

logger = logging.getLogger("mc-agent-server")

class ToolResult:
    """
    统一工具执行结果类。
    
    包含工具执行的成功状态、消息、数据和错误信息。
    """
    
    def __init__(
        self, 
        success: bool, 
        message: str = None, 
        data: Any = None, 
        error: str = None,
        request_id: str = None,
        response: Any = None
    ):
        """
        初始化工具结果。
        
        Args:
            success (bool): 操作是否成功
            message (str, optional): 成功或提示消息
            data (Any, optional): 返回的数据
            error (str, optional): 错误消息，如果操作失败
            request_id (str, optional): 请求ID
            response (Any, optional): 原始响应数据
        """
        self.success = success
        self.message = message
        self.data = data
        self.error = error
        self.request_id = request_id
        self.response = response
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将结果转换为字典。
        
        Returns:
            Dict[str, Any]: 结果字典
        """
        result = {"success": self.success}
        
        if self.message:
            result["message"] = self.message
        
        if self.data is not None:
            result["data"] = self.data
        
        if self.error:
            result["error"] = self.error
            
        if self.request_id:
            result["request_id"] = self.request_id
            
        if self.response:
            result["response"] = self.response
            
        return result
    
    @classmethod
    def success_result(cls, message: str = None, data: Any = None, request_id: str = None, response: Any = None) -> 'ToolResult':
        """
        创建成功结果。
        
        Args:
            message (str, optional): 成功消息
            data (Any, optional): 结果数据
            request_id (str, optional): 请求ID
            response (Any, optional): 原始响应数据
            
        Returns:
            ToolResult: 成功结果实例
        """
        return cls(True, message=message, data=data, request_id=request_id, response=response)
    
    @classmethod
    def error_result(cls, error: str, message: str = None) -> 'ToolResult':
        """
        创建错误结果。
        
        Args:
            error (str): 错误消息
            message (str, optional): 附加消息
            
        Returns:
            ToolResult: 错误结果实例
        """
        return cls(False, message=message, error=error)


class BaseTool:
    """
    工具基类。
    
    所有工具都应该继承此类，并实现execute方法。
    """
    
    def __init__(self, minecraft_server=None, mcp_server=None):
        """
        初始化工具。
        
        Args:
            minecraft_server: Minecraft服务器实例
            mcp_server: MCP服务器实例
        """
        self.minecraft_server = minecraft_server
        self.mcp_server = mcp_server
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具逻辑，子类应该实现此方法。
        
        Returns:
            ToolResult: 工具执行结果
        """
        raise NotImplementedError("Tool must implement execute method")
    
    def update_minecraft_server(self, minecraft_server):
        """
        更新Minecraft服务器引用。
        
        Args:
            minecraft_server: 新的Minecraft服务器实例
        """
        self.minecraft_server = minecraft_server
    
    def update_mcp_server(self, mcp_server):
        """
        更新MCP服务器引用。
        
        Args:
            mcp_server: 新的MCP服务器实例
        """
        self.mcp_server = mcp_server


class ToolRegistry:
    """
    工具注册表，用于管理所有可用的工具。
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self.tools: Dict[str, Type[BaseTool]] = {}
        self.tool_instances: Dict[str, BaseTool] = {}
        self.minecraft_server = None
        self.mcp_server = None
    
    def register_tool(self, name: str, tool_class: Type[BaseTool]):
        """
        注册工具类。
        
        Args:
            name (str): 工具名称
            tool_class (Type[BaseTool]): 工具类
        """
        self.tools[name] = tool_class
        logger.info(f"工具类已注册: {name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取工具实例。
        
        Args:
            name (str): 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例，如果不存在则为None
        """
        # 如果实例尚未创建，则创建它
        if name in self.tools and name not in self.tool_instances:
            self.tool_instances[name] = self.tools[name](
                minecraft_server=self.minecraft_server,
                mcp_server=self.mcp_server
            )
        
        return self.tool_instances.get(name)
    
    def update_minecraft_server(self, minecraft_server):
        """
        更新所有工具的Minecraft服务器引用。
        
        Args:
            minecraft_server: 新的Minecraft服务器实例
        """
        self.minecraft_server = minecraft_server
        
        # 更新所有已实例化的工具
        for tool in self.tool_instances.values():
            tool.update_minecraft_server(minecraft_server)
    
    def update_mcp_server(self, mcp_server):
        """
        更新所有工具的MCP服务器引用。
        
        Args:
            mcp_server: 新的MCP服务器实例
        """
        self.mcp_server = mcp_server
        
        # 更新所有已实例化的工具
        for tool in self.tool_instances.values():
            tool.update_mcp_server(mcp_server)
    
    def get_all_tool_names(self) -> List[str]:
        """
        获取所有已注册工具的名称。
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
    
    def get_tool_doc(self, name: str) -> Optional[str]:
        """
        获取工具的文档字符串。
        
        Args:
            name (str): 工具名称
            
        Returns:
            Optional[str]: 工具文档字符串，如果不存在则为None
        """
        if name in self.tools:
            return inspect.getdoc(self.tools[name].execute)
        return None


# 创建全局工具注册表实例
tool_registry = ToolRegistry()


def register_tool(name: str):
    """
    工具注册装饰器。
    
    Args:
        name (str): 工具名称
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(cls):
        tool_registry.register_tool(name, cls)
        return cls
    return decorator 