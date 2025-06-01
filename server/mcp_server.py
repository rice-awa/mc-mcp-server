import logging
import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Union

logger = logging.getLogger("mc-mcp-server")

class MCPServer:
    """
    MCP (Model Context Protocol) server implementation.
    
    This class manages MCP resources and tools, providing a bridge between
    the Minecraft WebSocket server and LLM APIs.
    """
    
    def __init__(self, config, minecraft_server=None):
        """
        Initialize the MCP server.
        
        Args:
            config (dict): Server configuration
            minecraft_server (MinecraftServer, optional): Reference to the Minecraft server instance
        """
        self.config = config
        self.minecraft_server = minecraft_server
        self.name = config.get("mcp", {}).get("name", "Minecraft Assistant")
        self.description = config.get("mcp", {}).get("description", "")
        self.version = config.get("mcp", {}).get("version", "1.0.0")
        
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
    
    async def handle_mcp_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.
        
        Args:
            client_id (str): Client identifier
            request (dict): MCP request object
            
        Returns:
            dict: MCP response object
        """
        logger.debug(f"Handling MCP request from client {client_id}: {request}")
        
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
            logger.warning(f"Unknown MCP request type: {request_type}")
            return {
                "error": {
                    "code": "invalid_request",
                    "message": f"Unknown request type: {request_type}"
                }
            }
    
    async def _handle_prompt_request(self, client_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP prompt request.
        
        Args:
            client_id (str): Client identifier
            request (dict): MCP prompt request
            
        Returns:
            dict: MCP response object
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
        Handle an MCP resource request.
        
        Args:
            client_id (str): Client identifier
            request (dict): MCP resource request
            
        Returns:
            dict: MCP response object
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
        Handle an MCP tool request.
        
        Args:
            client_id (str): Client identifier
            request (dict): MCP tool request
            
        Returns:
            dict: MCP response object
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
            pattern (str): Pattern with parameter placeholders
            
        Returns:
            dict: Extracted parameters
        """
        params = {}
        uri_parts = uri.split("/")
        pattern_parts = pattern.split("/")
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                # Extract parameter name
                param_name = pattern_part[1:-1]
                params[param_name] = uri_parts[i]
        
        return params
    
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