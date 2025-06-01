import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mc-agent-server")

# Global MCP server instance
# This will be set when the MCP server is initialized
mcp_server = None

async def send_script_event(client_id: str, event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a script event to the game.
    
    Args:
        client_id (str): Client identifier
        event_id (str): Event identifier
        data (dict): Event data
    
    Returns:
        dict: Script event result
    
    Raises:
        ValueError: If script event sending fails
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Format the data as JSON
    json_data = json.dumps(data).replace('"', '\\"')  # Escape double quotes
    
    # Send script event to the game
    success = await mcp_server.minecraft_server.send_script_event(client_id, event_id, json_data)
    if not success:
        logger.error(f"Failed to send script event: {event_id}")
        raise ValueError(f"Failed to send script event: {event_id}")
    
    return {
        "success": True,
        "event_id": event_id,
        "data": data
    }

async def get_player_position(client_id: str, player_name: str) -> Dict[str, Any]:
    """
    Get the position of a player using the script API.
    
    Args:
        client_id (str): Client identifier
        player_name (str): Name of the player
    
    Returns:
        dict: Player position
    """
    data = {"playerName": player_name}
    result = await send_script_event(client_id, "server:getPlayerPosition", data)
    
    # In a real implementation, we would wait for the response
    # Here, we just return a placeholder
    return {
        "player": player_name,
        "position": {"x": 0, "y": 0, "z": 0},
        "dimension": "overworld"
    }

async def set_block(client_id: str, x: int, y: int, z: int, block_type: str, block_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Set a block at the specified coordinates using the script API.
    
    Args:
        client_id (str): Client identifier
        x (int): X coordinate
        y (int): Y coordinate
        z (int): Z coordinate
        block_type (str): Block type
        block_data (dict, optional): Block data
    
    Returns:
        dict: Set block result
    """
    data = {
        "position": {"x": x, "y": y, "z": z},
        "blockType": block_type
    }
    
    if block_data:
        data["blockData"] = block_data
    
    return await send_script_event(client_id, "server:setBlock", data)

async def spawn_entity(client_id: str, entity_type: str, x: float, y: float, z: float, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Spawn an entity at the specified coordinates using the script API.
    
    Args:
        client_id (str): Client identifier
        entity_type (str): Entity type
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
        tags (list, optional): Entity tags
    
    Returns:
        dict: Spawn entity result
    """
    data = {
        "entityType": entity_type,
        "position": {"x": x, "y": y, "z": z}
    }
    
    if tags:
        data["tags"] = tags
    
    return await send_script_event(client_id, "server:spawnEntity", data)

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
    server.register_tool("send_script_event", send_script_event)
    server.register_tool("get_player_position", get_player_position)
    server.register_tool("set_block", set_block)
    server.register_tool("spawn_entity", spawn_entity) 