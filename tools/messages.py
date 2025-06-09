"""
消息工具包 - 提供Minecraft聊天和显示相关功能

这个模块包含与Minecraft消息显示相关的工具，如发送聊天消息、
显示标题和副标题、在动作栏显示消息等功能。
"""

import logging
from typing import Dict, Any, List, Optional
from server.utils.tools import BaseTool, ToolResult, register_tool, tool_registry

logger = logging.getLogger("mc-agent-server")

@register_tool("send_message")
class SendMessageTool(BaseTool):
    """发送消息到游戏聊天的工具"""
    
    async def execute(self, message: str, client_id: str = None, target: Optional[str] = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        发送消息到游戏聊天。
        
        Args:
            message (str): 要发送的消息
            client_id (str, optional): 客户端ID
            target (str, optional): 目标玩家名称，如果为None，则发送给所有玩家
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 消息发送结果
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 使用第一个可用的连接，如果未指定client_id
            if not client_id and self.minecraft_server.active_connections:
                client_id = next(iter(self.minecraft_server.active_connections.keys()))
            
            if not client_id:
                return ToolResult.error_result("没有活跃的Minecraft连接")
            
            # 格式化消息
            formatted_message = message.replace('"', '\\"')  # 转义双引号
            
            if target:
                # 发送消息给特定玩家
                command = f'tellraw {target} {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
            else:
                # 发送消息给所有玩家
                command = f'tellraw @a {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
            
            # 获取ExecuteCommandTool的实例
            execute_tool = tool_registry.get_tool("execute_command")
            if execute_tool:
                # 使用execute_command工具
                result = await execute_tool.execute(
                    command=command, 
                    client_id=client_id, 
                    wait_response=wait_response
                )
                
                # 如果成功，更新消息
                if result.success:
                    result.message = f"已发送消息: {message}"
                    result.data = {
                        "message": formatted_message,
                        "target": target or "all"
                    }
                
                return result
            else:
                # 直接发送命令到游戏
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result(f"发送消息失败: {message}")
                
                return ToolResult.success_result(
                    message=f"已发送消息: {message}",
                    data={
                        "message": formatted_message,
                        "target": target or "all"
                    },
                    request_id=request_id,
                    response=response
                )
        except Exception as e:
            logger.error(f"发送消息时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e))


@register_tool("broadcast_title")
class BroadcastTitleTool(BaseTool):
    """向所有玩家显示标题的工具"""
    
    async def execute(self, title: str, subtitle: Optional[str] = None, 
                     fade_in: int = 10, stay: int = 70, fade_out: int = 20, 
                     client_id: str = None, wait_response: bool = False) -> ToolResult:
        """
        向所有玩家显示标题。
        
        Args:
            title (str): 标题文本
            subtitle (str, optional): 副标题文本
            fade_in (int, optional): 淡入时间（刻）。默认为10。
            stay (int, optional): 停留时间（刻）。默认为70。
            fade_out (int, optional): 淡出时间（刻）。默认为20。
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 标题显示结果
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 使用第一个可用的连接，如果未指定client_id
            if not client_id and self.minecraft_server.active_connections:
                client_id = next(iter(self.minecraft_server.active_connections.keys()))
            
            if not client_id:
                return ToolResult.error_result("没有活跃的Minecraft连接")
            
            # 获取ExecuteCommandTool的实例
            execute_tool = tool_registry.get_tool("execute_command")
            
            # 设置标题时间
            times_command = f"title @a times {fade_in} {stay} {fade_out}"
            if execute_tool:
                await execute_tool.execute(
                    command=times_command, 
                    client_id=client_id, 
                    wait_response=False
                )
            else:
                await self.minecraft_server.run_command(client_id, times_command)
            
            # 发送标题
            title_command = f'title @a title "{title}"'
            if execute_tool:
                await execute_tool.execute(
                    command=title_command, 
                    client_id=client_id, 
                    wait_response=False
                )
            else:
                await self.minecraft_server.run_command(client_id, title_command)
            
            # 如果提供了副标题，则发送副标题
            if subtitle:
                subtitle_command = f'title @a subtitle "{subtitle}"'
                if execute_tool:
                    result = await execute_tool.execute(
                        command=subtitle_command, 
                        client_id=client_id, 
                        wait_response=wait_response
                    )
                    
                    if result.success:
                        return ToolResult.success_result(
                            message=f"已显示标题和副标题",
                            data={
                                "title": title,
                                "subtitle": subtitle
                            },
                            request_id=result.request_id,
                            response=result.response
                        )
                    else:
                        return result
                else:
                    success, request_id, response = await self.minecraft_server.run_command(
                        client_id, 
                        subtitle_command, 
                        wait_for_response=wait_response
                    )
                    
                    if not success:
                        return ToolResult.error_result("显示副标题失败")
                    
                    return ToolResult.success_result(
                        message=f"已显示标题和副标题",
                        data={
                            "title": title,
                            "subtitle": subtitle
                        },
                        request_id=request_id,
                        response=response
                    )
            else:
                # 如果没有副标题，返回标题命令的结果
                return ToolResult.success_result(
                    message=f"已显示标题",
                    data={
                        "title": title,
                        "subtitle": None
                    }
                )
        except Exception as e:
            logger.error(f"显示标题时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e))


@register_tool("send_action_bar")
class SendActionBarTool(BaseTool):
    """发送消息到动作栏的工具"""
    
    async def execute(self, message: str, client_id: str = None, target: Optional[str] = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        发送消息到动作栏。
        
        Args:
            message (str): 要发送的消息
            client_id (str, optional): 客户端ID
            target (str, optional): 目标玩家名称，如果为None，则发送给所有玩家
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 动作栏消息结果
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 使用第一个可用的连接，如果未指定client_id
            if not client_id and self.minecraft_server.active_connections:
                client_id = next(iter(self.minecraft_server.active_connections.keys()))
            
            if not client_id:
                return ToolResult.error_result("没有活跃的Minecraft连接")
            
            # 格式化消息
            formatted_message = message.replace('"', '\\"')  # 转义双引号
            
            target_selector = target or "@a"
            command = f'title {target_selector} actionbar "{formatted_message}"'
            
            # 获取ExecuteCommandTool的实例
            execute_tool = tool_registry.get_tool("execute_command")
            if execute_tool:
                # 使用execute_command工具
                result = await execute_tool.execute(
                    command=command, 
                    client_id=client_id, 
                    wait_response=wait_response
                )
                
                # 如果成功，更新消息
                if result.success:
                    result.message = f"已发送动作栏消息: {message}"
                    result.data = {
                        "message": formatted_message,
                        "target": target or "all"
                    }
                
                return result
            else:
                # 直接发送命令到游戏
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result(f"发送动作栏消息失败: {message}")
                
                return ToolResult.success_result(
                    message=f"已发送动作栏消息: {message}",
                    data={
                        "message": formatted_message,
                        "target": target or "all"
                    },
                    request_id=request_id,
                    response=response
                )
        except Exception as e:
            logger.error(f"发送动作栏消息时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e)) 