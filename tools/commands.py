import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("mc-mcp-server")

# Global MCP server instance
# This will be set when the MCP server is initialized
mcp_server = None

async def execute_command(client_id: str, command: str) -> Dict[str, Any]:
    """
    Execute a Minecraft command.
    
    Args:
        client_id (str): Client identifier
        command (str): Command to execute
    
    Returns:
        dict: Command execution result
    
    Raises:
        ValueError: If command execution fails
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Send command to the game
    success = await mcp_server.minecraft_server.run_command(client_id, command)
    if not success:
        logger.error(f"Failed to execute command: {command}")
        raise ValueError(f"Failed to execute command: {command}")
    
    return {
        "success": True,
        "message": f"Command executed: {command}"
    }

async def teleport_player(client_id: str, player_name: str, x: float, y: float, z: float, dimension: Optional[str] = None) -> Dict[str, Any]:
    """
    Teleport a player to specified coordinates.
    
    Args:
        client_id (str): Client identifier
        player_name (str): Name of the player to teleport
        x (float): X coordinate
        y (float): Y coordinate
        z (float): Z coordinate
        dimension (str, optional): Dimension to teleport to. Defaults to current dimension.
    
    Returns:
        dict: Teleport result
    """
    if dimension:
        command = f"tp {player_name} {x} {y} {z} {dimension}"
    else:
        command = f"tp {player_name} {x} {y} {z}"
    
    return await execute_command(client_id, command)

async def give_item(client_id: str, player_name: str, item: str, amount: int = 1, data: int = 0) -> Dict[str, Any]:
    """
    Give an item to a player.
    
    Args:
        client_id (str): Client identifier
        player_name (str): Name of the player
        item (str): Item identifier
        amount (int, optional): Amount of items. Defaults to 1.
        data (int, optional): Item data value. Defaults to 0.
    
    Returns:
        dict: Result of the give command
    """
    command = f"give {player_name} {item} {amount} {data}"
    return await execute_command(client_id, command)

async def set_game_rule(client_id: str, rule: str, value: str) -> Dict[str, Any]:
    """
    Set a game rule.
    
    Args:
        client_id (str): Client identifier
        rule (str): Game rule name
        value (str): Game rule value
    
    Returns:
        dict: Result of the gamerule command
    """
    command = f"gamerule {rule} {value}"
    return await execute_command(client_id, command)

async def change_gamemode(client_id: str, player_name: str, gamemode: str) -> Dict[str, Any]:
    """
    Change a player's gamemode.
    
    Args:
        client_id (str): Client identifier
        player_name (str): Name of the player
        gamemode (str): Gamemode to set (survival, creative, adventure, spectator)
    
    Returns:
        dict: Result of the gamemode command
    """
    command = f"gamemode {gamemode} {player_name}"
    return await execute_command(client_id, command)

# Register tools with the MCP server
def register_tools(server):
    """
    Register command tools with the MCP server.
    
    Args:
        server: MCP server instance
    """
    global mcp_server
    mcp_server = server
    
    # Register tool handlers
    server.register_tool("execute_command", execute_command)
    server.register_tool("teleport_player", teleport_player)
    server.register_tool("give_item", give_item)
    server.register_tool("set_game_rule", set_game_rule)
    server.register_tool("change_gamemode", change_gamemode) 