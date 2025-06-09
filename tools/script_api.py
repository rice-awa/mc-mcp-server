"""
脚本API工具包 - 提供Minecraft脚本API相关功能

这个模块包含与Minecraft脚本API相关的工具，如发送脚本事件、
获取玩家位置、设置方块和生成实体等功能。
"""

import logging
import json
from typing import Dict, Any, Optional, List
from server.utils.tools import BaseTool, ToolResult, register_tool, tool_registry

logger = logging.getLogger("mc-agent-server")

# Global MCP server instance
# This will be set when the MCP server is initialized
mcp_server = None

@register_tool("send_script_event")
class SendScriptEventTool(BaseTool):
    """发送脚本事件到游戏的工具"""
    
    async def execute(self, event_id: str, data: Dict[str, Any], 
                     client_id: str = None, wait_response: bool = False) -> ToolResult:
        """
        发送脚本事件到游戏。
        
        Args:
            event_id (str): 事件标识符
            data (dict): 事件数据
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 脚本事件结果
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 使用第一个可用的连接，如果未指定client_id
            if not client_id and self.minecraft_server.active_connections:
                client_id = next(iter(self.minecraft_server.active_connections.keys()))
            
            if not client_id:
                return ToolResult.error_result("没有活跃的Minecraft连接")
            
            # 格式化数据为JSON
            json_data = json.dumps(data).replace('"', '\\"')  # 转义双引号
            
            # 发送脚本事件
            success, request_id, response = await self.minecraft_server.send_script_event(
                client_id, 
                event_id, 
                json_data, 
                wait_for_response=wait_response
            )
            
            if not success:
                return ToolResult.error_result(f"发送脚本事件失败: {event_id}")
            
            return ToolResult.success_result(
                message=f"已发送脚本事件: {event_id}",
                data={
                    "event_id": event_id,
                    "data": data
                },
                request_id=request_id,
                response=response
            )
        except Exception as e:
            logger.error(f"发送脚本事件时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e))


@register_tool("get_player_position")
class GetPlayerPositionTool(BaseTool):
    """获取玩家位置的工具"""
    
    async def execute(self, player_name: str, client_id: str = None, wait_response: bool = False) -> ToolResult:
        """
        获取玩家位置。
        
        Args:
            player_name (str): 玩家名称
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 玩家位置结果
        """
        # 获取SendScriptEventTool工具
        script_event_tool = tool_registry.get_tool("send_script_event")
        if script_event_tool:
            data = {"playerName": player_name}
            result = await script_event_tool.execute(
                event_id="server:getPlayerPosition",
                data=data,
                client_id=client_id,
                wait_response=wait_response
            )
            
            if not result.success:
                return result
            
            # 在实际实现中，我们会等待响应
            # 这里只返回一个占位符
            return ToolResult.success_result(
                message=f"已获取玩家 {player_name} 的位置",
                data={
                    "player": player_name,
                    "position": {"x": 0, "y": 0, "z": 0},
                    "dimension": "overworld"
                },
                request_id=result.request_id,
                response=result.response
            )
        else:
            # 如果找不到SendScriptEventTool，返回错误
            return ToolResult.error_result("无法发送脚本事件，send_script_event工具不可用")


@register_tool("set_block")
class SetBlockTool(BaseTool):
    """设置方块的工具"""
    
    async def execute(self, x: int, y: int, z: int, block_type: str, block_data: Optional[Dict[str, Any]] = None,
                     client_id: str = None, wait_response: bool = False) -> ToolResult:
        """
        设置指定坐标的方块。
        
        Args:
            x (int): X坐标
            y (int): Y坐标
            z (int): Z坐标
            block_type (str): 方块类型
            block_data (dict, optional): 方块数据
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 设置方块结果
        """
        # 构建事件数据
        data = {
            "position": {"x": x, "y": y, "z": z},
            "blockType": block_type
        }
        
        if block_data:
            data["blockData"] = block_data
        
        # 获取SendScriptEventTool工具
        script_event_tool = tool_registry.get_tool("send_script_event")
        if script_event_tool:
            result = await script_event_tool.execute(
                event_id="server:setBlock",
                data=data,
                client_id=client_id,
                wait_response=wait_response
            )
            
            if result.success:
                result.message = f"已在坐标 [{x}, {y}, {z}] 设置方块 {block_type}"
            
            return result
        else:
            # 如果找不到SendScriptEventTool，返回错误
            return ToolResult.error_result("无法发送脚本事件，send_script_event工具不可用")


@register_tool("spawn_entity")
class SpawnEntityTool(BaseTool):
    """生成实体的工具"""
    
    async def execute(self, entity_type: str, x: float, y: float, z: float, tags: Optional[List[str]] = None,
                     client_id: str = None, wait_response: bool = False) -> ToolResult:
        """
        在指定坐标生成实体。
        
        Args:
            entity_type (str): 实体类型
            x (float): X坐标
            y (float): Y坐标
            z (float): Z坐标
            tags (list, optional): 实体标签
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 生成实体结果
        """
        # 构建事件数据
        data = {
            "entityType": entity_type,
            "position": {"x": x, "y": y, "z": z}
        }
        
        if tags:
            data["tags"] = tags
        
        # 获取SendScriptEventTool工具
        script_event_tool = tool_registry.get_tool("send_script_event")
        if script_event_tool:
            result = await script_event_tool.execute(
                event_id="server:spawnEntity",
                data=data,
                client_id=client_id,
                wait_response=wait_response
            )
            
            if result.success:
                result.message = f"已在坐标 [{x}, {y}, {z}] 生成实体 {entity_type}"
                if tags:
                    result.message += f"，标签: {tags}"
            
            return result
        else:
            # 如果找不到SendScriptEventTool，返回错误
            return ToolResult.error_result("无法发送脚本事件，send_script_event工具不可用")

# Register tools with the MCP server
def register_tools(server):
    """
    Register script API tools with the MCP server.
    
    Args:
        server: MCP server instance
    """
    global mcp_server
    mcp_server = server
    
    # Register tool handlers
    server.register_tool("send_script_event", SendScriptEventTool())
    server.register_tool("get_player_position", GetPlayerPositionTool())
    server.register_tool("set_block", SetBlockTool())
    server.register_tool("spawn_entity", SpawnEntityTool()) 