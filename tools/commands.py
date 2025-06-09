"""
命令工具包 - 提供Minecraft命令执行相关功能

这个模块包含与Minecraft命令执行相关的工具，如执行命令、传送玩家、
给予物品、设置游戏规则和更改游戏模式等功能。
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from server.utils.tools import BaseTool, ToolResult, register_tool, tool_registry

logger = logging.getLogger("mc-agent-server")

@register_tool("execute_command")
class ExecuteCommandTool(BaseTool):
    """执行Minecraft命令的工具"""
    
    async def execute(self, command: str, client_id: str = None, wait_response: bool = True) -> ToolResult:
        """
        执行Minecraft命令。
        
        Args:
            command (str): 要执行的命令
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 命令执行结果，包含响应数据
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 使用第一个可用的连接，如果未指定client_id
            if not client_id and self.minecraft_server.active_connections:
                client_id = next(iter(self.minecraft_server.active_connections.keys()))
            
            if not client_id:
                return ToolResult.error_result("没有活跃的Minecraft连接")
            
            # 执行命令并等待响应
            success, request_id, response = await self.minecraft_server.run_command(
                client_id, 
                command, 
                wait_for_response=wait_response
            )
            
            if not success:
                return ToolResult.error_result("命令发送失败")
            
            # 返回结果
            return ToolResult.success_result(
                message=f"命令已执行: {command}",
                request_id=request_id,
                response=response
            )
        except Exception as e:
            logger.error(f"执行命令时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e))


@register_tool("teleport_player")
class TeleportPlayerTool(BaseTool):
    """传送玩家到指定坐标的工具"""
    
    async def execute(self, player_name: str, x: float, y: float, z: float, 
                     client_id: str = None, dimension: str = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        传送玩家到指定坐标。
        
        Args:
            player_name (str): 玩家名称
            x (float): X坐标
            y (float): Y坐标
            z (float): Z坐标
            client_id (str, optional): 客户端ID
            dimension (str, optional): 维度名称
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 传送结果，包含响应数据
        """
        if not self.minecraft_server:
            return ToolResult.error_result("Minecraft服务器未连接")
        
        try:
            # 构建命令
            if dimension:
                command = f"tp {player_name} {x} {y} {z} {dimension}"
            else:
                command = f"tp {player_name} {x} {y} {z}"
            
            # 获取ExecuteCommandTool的实例
            execute_tool = tool_registry.get_tool("execute_command")
            if not execute_tool:
                # 如果工具不可用，直接执行命令
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id or next(iter(self.minecraft_server.active_connections.keys())), 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result("命令发送失败")
                
                return ToolResult.success_result(
                    message=f"已传送玩家 {player_name} 到坐标 [{x}, {y}, {z}]" + (f" 维度: {dimension}" if dimension else ""),
                    request_id=request_id,
                    response=response
                )
            else:
                # 使用execute_command工具
                result = await execute_tool.execute(
                    command=command, 
                    client_id=client_id, 
                    wait_response=wait_response
                )
                
                # 如果成功，更新消息
                if result.success:
                    result.message = f"已传送玩家 {player_name} 到坐标 [{x}, {y}, {z}]" + (f" 维度: {dimension}" if dimension else "")
                
                return result
        except Exception as e:
            logger.error(f"传送玩家时出错: {e}", exc_info=True)
            return ToolResult.error_result(str(e))


@register_tool("give_item")
class GiveItemTool(BaseTool):
    """给予玩家物品的工具"""
    
    async def execute(self, player_name: str, item: str, amount: int = 1, 
                     data: int = 0, client_id: str = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        给予玩家物品。
        
        Args:
            player_name (str): 玩家名称
            item (str): 物品ID
            amount (int, optional): 数量，默认为1
            data (int, optional): 物品数据值，默认为0
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 给予物品结果，包含响应数据
        """
        command = f"give {player_name} {item} {amount} {data}"
        
        # 获取ExecuteCommandTool的实例
        execute_tool = tool_registry.get_tool("execute_command")
        if execute_tool:
            result = await execute_tool.execute(
                command=command, 
                client_id=client_id, 
                wait_response=wait_response
            )
            
            # 如果成功，更新消息
            if result.success:
                result.message = f"已给予玩家 {player_name} {amount}个 {item}"
            
            return result
        else:
            # 直接使用minecraft_server执行命令
            if not self.minecraft_server:
                return ToolResult.error_result("Minecraft服务器未连接")
                
            try:
                # 获取客户端ID
                if not client_id and self.minecraft_server.active_connections:
                    client_id = next(iter(self.minecraft_server.active_connections.keys()))
                
                if not client_id:
                    return ToolResult.error_result("没有活跃的Minecraft连接")
                
                # 执行命令
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result("命令发送失败")
                
                return ToolResult.success_result(
                    message=f"已给予玩家 {player_name} {amount}个 {item}",
                    request_id=request_id,
                    response=response
                )
            except Exception as e:
                logger.error(f"给予物品时出错: {e}", exc_info=True)
                return ToolResult.error_result(str(e))


@register_tool("set_game_rule")
class SetGameRuleTool(BaseTool):
    """设置游戏规则的工具"""
    
    async def execute(self, rule: str, value: str, client_id: str = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        设置游戏规则。
        
        Args:
            rule (str): 规则名称
            value (str): 规则值
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 设置结果，包含响应数据
        """
        command = f"gamerule {rule} {value}"
        
        # 使用ExecuteCommandTool执行命令
        execute_tool = tool_registry.get_tool("execute_command")
        if execute_tool:
            result = await execute_tool.execute(
                command=command, 
                client_id=client_id, 
                wait_response=wait_response
            )
            
            # 如果成功，更新消息
            if result.success:
                result.message = f"已设置游戏规则 {rule} 为 {value}"
            
            return result
        else:
            # 直接使用minecraft_server执行命令
            if not self.minecraft_server:
                return ToolResult.error_result("Minecraft服务器未连接")
                
            try:
                # 获取客户端ID
                if not client_id and self.minecraft_server.active_connections:
                    client_id = next(iter(self.minecraft_server.active_connections.keys()))
                
                if not client_id:
                    return ToolResult.error_result("没有活跃的Minecraft连接")
                
                # 执行命令
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result("命令发送失败")
                
                return ToolResult.success_result(
                    message=f"已设置游戏规则 {rule} 为 {value}",
                    request_id=request_id,
                    response=response
                )
            except Exception as e:
                logger.error(f"设置游戏规则时出错: {e}", exc_info=True)
                return ToolResult.error_result(str(e))


@register_tool("change_gamemode")
class ChangeGamemodeTool(BaseTool):
    """更改玩家游戏模式的工具"""
    
    async def execute(self, player_name: str, gamemode: str, client_id: str = None, 
                     wait_response: bool = False) -> ToolResult:
        """
        更改玩家的游戏模式。
        
        Args:
            player_name (str): 玩家名称
            gamemode (str): 游戏模式 (survival, creative, adventure, spectator)
            client_id (str, optional): 客户端ID
            wait_response (bool, optional): 是否等待命令响应
            
        Returns:
            ToolResult: 更改结果，包含响应数据
        """
        # 验证游戏模式
        valid_gamemodes = ["survival", "creative", "adventure", "spectator"]
        if gamemode.lower() not in valid_gamemodes:
            return ToolResult.error_result(
                f"无效的游戏模式: {gamemode}，有效值为: {', '.join(valid_gamemodes)}"
            )
        
        command = f"gamemode {gamemode} {player_name}"
        
        # 使用ExecuteCommandTool执行命令
        execute_tool = tool_registry.get_tool("execute_command")
        if execute_tool:
            result = await execute_tool.execute(
                command=command, 
                client_id=client_id, 
                wait_response=wait_response
            )
            
            # 如果成功，更新消息
            if result.success:
                result.message = f"已将玩家 {player_name} 的游戏模式更改为 {gamemode}"
            
            return result
        else:
            # 直接使用minecraft_server执行命令
            if not self.minecraft_server:
                return ToolResult.error_result("Minecraft服务器未连接")
                
            try:
                # 获取客户端ID
                if not client_id and self.minecraft_server.active_connections:
                    client_id = next(iter(self.minecraft_server.active_connections.keys()))
                
                if not client_id:
                    return ToolResult.error_result("没有活跃的Minecraft连接")
                
                # 执行命令
                success, request_id, response = await self.minecraft_server.run_command(
                    client_id, 
                    command, 
                    wait_for_response=wait_response
                )
                
                if not success:
                    return ToolResult.error_result("命令发送失败")
                
                return ToolResult.success_result(
                    message=f"已将玩家 {player_name} 的游戏模式更改为 {gamemode}",
                    request_id=request_id,
                    response=response
                )
            except Exception as e:
                logger.error(f"更改游戏模式时出错: {e}", exc_info=True)
                return ToolResult.error_result(str(e)) 