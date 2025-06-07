import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("mc-agent-server")

# Global MCP server instance
# This will be set when the MCP server is initialized
mcp_server = None

async def send_message(client_id: str, message: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a message to the game chat.
    
    Args:
        client_id (str): Client identifier
        message (str): Message to send
        target (str, optional): Target player name. If None, sends to all players.
    
    Returns:
        dict: Message sending result
    
    Raises:
        ValueError: If message sending fails
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Format the message
    formatted_message = message.replace('"', '\\"')  # Escape double quotes
    
    if target:
        # Send a message to a specific player
        command = f'tellraw {target} {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
    else:
        # Send a message to all players
        command = f'tellraw @a {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
    
    # Send command to the game
    success = await mcp_server.minecraft_server.run_command(client_id, command)
    if not success:
        logger.error(f"Failed to send message: {message}")
        raise ValueError(f"Failed to send message: {message}")
    
    return {
        "success": True,
        "message": formatted_message,
        "target": target or "all"
    }

async def broadcast_title(client_id: str, title: str, subtitle: Optional[str] = None, fade_in: int = 10, stay: int = 70, fade_out: int = 20) -> Dict[str, Any]:
    """
    Display a title message to all players.
    
    Args:
        client_id (str): Client identifier
        title (str): Title text
        subtitle (str, optional): Subtitle text
        fade_in (int, optional): Fade in time in ticks. Defaults to 10.
        stay (int, optional): Stay time in ticks. Defaults to 70.
        fade_out (int, optional): Fade out time in ticks. Defaults to 20.
    
    Returns:
        dict: Title display result
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Set title times
    times_command = f"title @a times {fade_in} {stay} {fade_out}"
    await mcp_server.minecraft_server.run_command(client_id, times_command)
    
    # Send title
    title_command = f'title @a title "{title}"'
    await mcp_server.minecraft_server.run_command(client_id, title_command)
    
    # Send subtitle if provided
    if subtitle:
        subtitle_command = f'title @a subtitle "{subtitle}"'
        await mcp_server.minecraft_server.run_command(client_id, subtitle_command)
    
    return {
        "success": True,
        "title": title,
        "subtitle": subtitle
    }

async def send_action_bar(client_id: str, message: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a message to the action bar.
    
    Args:
        client_id (str): Client identifier
        message (str): Message to send
        target (str, optional): Target player name. If None, sends to all players.
    
    Returns:
        dict: Action bar message result
    """
    if not mcp_server or not mcp_server.minecraft_server:
        logger.error("Minecraft server not available")
        raise ValueError("Minecraft server not available")
    
    # Format the message
    formatted_message = message.replace('"', '\\"')  # Escape double quotes
    
    target_selector = target or "@a"
    command = f'title {target_selector} actionbar "{formatted_message}"'
    
    # Send command to the game
    success = await mcp_server.minecraft_server.run_command(client_id, command)
    if not success:
        logger.error(f"Failed to send action bar message: {message}")
        raise ValueError(f"Failed to send action bar message: {message}")
    
    return {
        "success": True,
        "message": formatted_message,
        "target": target or "all"
    }

# Register tools with the MCP server
def register_tools(server):
    """
    Register message tools with the MCP server.
    
    Args:
        server: MCP server instance
    """
    global mcp_server
    mcp_server = server
    
    # Register tool handlers
    server.register_tool("send_message", send_message)
    server.register_tool("broadcast_title", broadcast_title)
    server.register_tool("send_action_bar", send_action_bar) 