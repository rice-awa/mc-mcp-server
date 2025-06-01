import logging
from typing import Dict, Any

logger = logging.getLogger("mc-agent-server")

# Global MCP server instance
# This will be set when the MCP server is initialized
mcp_server = None

async def get_player_info(client_id: str, player_name: str) -> Dict[str, Any]:
    """
    Get information about a player.
    
    Args:
        client_id (str): Client identifier
        player_name (str): Name of the player, or "current" for the current player
    
    Returns:
        dict: Player information
    
    Raises:
        ValueError: If player not found or other error occurs
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Command to get player information using the script API
    command = f"scriptevent server:getPlayerInfo {player_name}"
    
    # Send command to the game
    success = await mcp_server.minecraft_server.run_command(client_id, command)
    if not success:
        logger.error(f"Failed to send command to get player info for {player_name}")
        raise ValueError(f"Failed to get player info for {player_name}")
    
    # In a real implementation, we would wait for the response from the game
    # Here, we just return a placeholder
    return {
        "name": player_name,
        "position": {"x": 0, "y": 0, "z": 0},
        "health": 20,
        "level": 0,
        "gamemode": "survival"
    }

# Resource decorator for player information
def register_resources(server):
    """
    Register player resources with the MCP server.
    
    Args:
        server: MCP server instance
    """
    global mcp_server
    mcp_server = server
    
    # Register resource handlers
    server.register_resource("minecraft://player/{player_name}", get_player_info) 