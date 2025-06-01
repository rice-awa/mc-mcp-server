import logging
import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Union

logger = logging.getLogger("mc-agent-server")

class AgentServer:
    """
    Agent server implementation.
    
    This class manages Agent resources and tools, providing a bridge between
    the Minecraft WebSocket server and LLM APIs.
    """
    
    def __init__(self, config, minecraft_server=None):
        """
        Initialize the Agent server.
        
        Args:
            config (dict): Server configuration
            minecraft_server (MinecraftServer, optional): Reference to the Minecraft server instance
        """
        self.config = config
        self.minecraft_server = minecraft_server
        self.name = config.get("agent", {}).get("name", "Minecraft Assistant")
        self.description = config.get("agent", {}).get("description", "")
        self.version = config.get("agent", {}).get("version", "1.0.0")
        
        # Store registered resources and tools
        self.resources = {}
        self.tools = {}
        
        # Map of active LLM conversations by client ID
        self.conversations = {}
    
    def register_resource(self, uri_pattern: str, resource_func: Callable):
        """
        Register a resource handler function.
        
        Args:
            uri_pattern (str): URI pattern for the resource (e.g., "minecraft://player/{player_name}")
            resource_func (callable): Function to handle resource retrieval
        """
        self.resources[uri_pattern] = resource_func
        logger.info(f"Registered resource: {uri_pattern}")
    
    def register_tool(self, name: str, tool_func: Callable):
        """
        Register a tool function.
        
        Args:
            name (str): Name of the tool
            tool_func (callable): Function implementing the tool
        """
        self.tools[name] = tool_func
        logger.info(f"Registered tool: {name}")
    
    async def handle_agent_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an Agent request.
        
        Args:
            client_id (str): Client identifier
            request (dict): Agent request object
            
        Returns:
            dict: Agent response object
        """
        logger.debug(f"Handling Agent request from client {client_id}: {request}")
        
        # Extract request type and data
        request_type = request.get("type", "")
        
        if request_type == "prompt":
            # Handle prompt request
            return await self._handle_prompt_request(client_id, request)
        elif request_type == "resource":
            # Handle resource request
            return await self._handle_resource_request(client_id, request)
        elif request_type == "tool":
            # Handle tool request
            return await self._handle_tool_request(client_id, request)
        else:
            # Unknown request type
            logger.warning(f"Unknown Agent request type: {request_type}")
            return {
                "error": {
                    "code": "invalid_request",
                    "message": f"Unknown request type: {request_type}"
                }
            }
    
    async def _handle_prompt_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an Agent prompt request.
        
        Args:
            client_id (str): Client identifier
            request (dict): Agent prompt request
            
        Returns:
            dict: Agent response object
        """
        from .utils.llm import create_conversation
        
        prompt = request.get("prompt", "")
        if not prompt:
            return {
                "error": {
                    "code": "invalid_request",
                    "message": "Prompt is required"
                }
            }
        
        # Get or create conversation for this client
        if client_id not in self.conversations:
            try:
                self.conversations[client_id] = await create_conversation(self.config)
            except ValueError as e:
                return {
                    "error": {
                        "code": "config_error",
                        "message": str(e)
                    }
                }
        
        conversation = self.conversations[client_id]
        
        # Process through LLM
        response_content = []
        thinking_content = []
        
        async for chunk in conversation.call_gpt(prompt):
            if chunk.get("reasoning_content"):
                thinking_content.append(chunk["reasoning_content"])
            if chunk.get("content"):
                response_content.append(chunk["content"])
                
                # If Minecraft server is available, send message to the game
                if self.minecraft_server and client_id in self.minecraft_server.active_connections:
                    await self.minecraft_server.send_game_message(client_id, chunk["content"])
        
        # Combine chunks into full response
        full_response = "".join(response_content)
        full_thinking = "".join(thinking_content)
        
        return {
            "content": full_response,
            "thinking": full_thinking
        }
    
    async def _handle_resource_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an Agent resource request.
        
        Args:
            client_id (str): Client identifier
            request (dict): Agent resource request
            
        Returns:
            dict: Agent response object
        """
        uri = request.get("uri", "")
        if not uri:
            return {
                "error": {
                    "code": "invalid_request",
                    "message": "Resource URI is required"
                }
            }
        
        # Find matching resource handler
        for uri_pattern, resource_func in self.resources.items():
            # Simple pattern matching for now
            # In a full implementation, use regex or path matching library
            if self._match_uri_pattern(uri, uri_pattern):
                try:
                    # Extract parameters from URI
                    params = self._extract_uri_params(uri, uri_pattern)
                    
                    # Call resource handler
                    result = await resource_func(**params)
                    return {"data": result}
                except Exception as e:
                    logger.error(f"Error handling resource request: {e}", exc_info=True)
                    return {
                        "error": {
                            "code": "resource_error",
                            "message": str(e)
                        }
                    }
        
        # No matching resource found
        return {
            "error": {
                "code": "not_found",
                "message": f"Resource not found: {uri}"
            }
        }
    
    async def _handle_tool_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an Agent tool request.
        
        Args:
            client_id (str): Client identifier
            request (dict): Agent tool request
            
        Returns:
            dict: Agent response object
        """
        tool_name = request.get("name", "")
        if not tool_name:
            return {
                "error": {
                    "code": "invalid_request",
                    "message": "Tool name is required"
                }
            }
        
        parameters = request.get("parameters", {})
        
        # Find tool
        tool_func = self.tools.get(tool_name)
        if not tool_func:
            return {
                "error": {
                    "code": "not_found",
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            # Call tool function
            result = await tool_func(client_id=client_id, **parameters)
            return {"result": result}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "error": {
                    "code": "tool_error",
                    "message": str(e)
                }
            }
    
    def _match_uri_pattern(self, uri: str, pattern: str) -> bool:
        """
        Match a URI against a pattern.
        
        Args:
            uri (str): URI to match
            pattern (str): Pattern to match against
            
        Returns:
            bool: True if URI matches pattern, False otherwise
        """
        # Simple implementation - in a full version, use regex
        uri_parts = uri.split("/")
        pattern_parts = pattern.split("/")
        
        if len(uri_parts) != len(pattern_parts):
            return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                # Parameter part, matches anything
                continue
            if pattern_part != uri_parts[i]:
                return False
        
        return True
    
    def _extract_uri_params(self, uri: str, pattern: str) -> Dict[str, str]:
        """
        Extract parameters from a URI based on a pattern.
        
        Args:
            uri (str): URI to extract parameters from
            pattern (str): Pattern to match against
            
        Returns:
            dict: Extracted parameters
        """
        parts = uri.split("/")
        pattern_parts = pattern.split("/")
        
        params = {}
        for i, pattern_part in enumerate(pattern_parts):
            if i < len(parts) and pattern_part.startswith("{") and pattern_part.endswith("}"):
                param_name = pattern_part[1:-1]
                params[param_name] = parts[i]
        
        return params
    
    async def run(self, transport="stdio"):
        """
        启动Agent服务器。

        Args:
            transport (str): 传输方式，目前支持"stdio"
            
        Raises:
            ValueError: 如果传输方式不支持
        """
        logger.info(f"启动Agent服务器，使用 {transport} 传输")
        
        if transport == "stdio":
            # 使用标准输入/输出进行通信
            await self._run_stdio()
        else:
            raise ValueError(f"不支持的传输方式: {transport}")
    
    async def _run_stdio(self):
        """使用标准输入/输出运行Agent服务器"""
        import sys
        import json
        
        # 创建一个随机的客户端ID
        import uuid
        client_id = str(uuid.uuid4())
        
        # 发送欢迎消息
        welcome_message = {
            "type": "welcome",
            "server": self.name,
            "version": self.version,
            "client_id": client_id
        }
        print(json.dumps(welcome_message), flush=True)
        
        # 处理标准输入中的消息
        while True:
            try:
                # 读取一行输入
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    # EOF，退出循环
                    break
                
                # 解析JSON请求
                try:
                    request = json.loads(line)
                    
                    # 处理请求
                    response = await self.handle_agent_request(client_id, request)
                    
                    # 发送响应
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON请求: {line}")
                    print(json.dumps({
                        "error": {
                            "code": "invalid_request",
                            "message": "无效的JSON请求"
                        }
                    }), flush=True)
            except Exception as e:
                logger.error(f"处理请求时出错: {e}", exc_info=True)
                print(json.dumps({
                    "error": {
                        "code": "server_error",
                        "message": str(e)
                    }
                }), flush=True)
    
    async def close_conversation(self, client_id: str):
        """
        Close a conversation for a client.
        
        Args:
            client_id (str): Client identifier
        """
        if client_id in self.conversations:
            conversation = self.conversations[client_id]
            await conversation.clean_history()
            del self.conversations[client_id]
            logger.debug(f"Closed conversation for client {client_id}")
    
    async def close_all_conversations(self):
        """
        Close all active conversations.
        """
        for client_id in list(self.conversations.keys()):
            await self.close_conversation(client_id)
        logger.info("Closed all conversations")
    
    def get_tools(self) -> Dict[str, str]:
        """
        获取所有已注册的工具列表
        
        Returns:
            dict: 工具名称到描述的映射
        """
        tool_info = {}
        for name, tool_func in self.tools.items():
            # 获取工具函数的文档字符串作为描述
            description = tool_func.__doc__ or "无描述"
            # 确保去除前导空格和缩进
            description = "\n".join([line.strip() for line in description.split('\n')])
            tool_info[name] = description
        return tool_info
    
    def get_resources(self) -> Dict[str, str]:
        """
        获取所有已注册的资源列表
        
        Returns:
            dict: 资源URI模式到描述的映射
        """
        resource_info = {}
        for uri_pattern, resource_func in self.resources.items():
            # 获取资源函数的文档字符串作为描述
            description = resource_func.__doc__ or "无描述"
            # 确保去除前导空格和缩进
            description = "\n".join([line.strip() for line in description.split('\n')])
            resource_info[uri_pattern] = description
        return resource_info 