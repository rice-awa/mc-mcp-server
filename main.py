import os
import json
import asyncio
import logging
from dotenv import load_dotenv

from server.mc_server import MinecraftServer
from server.utils.logging import setup_logging
from mcp.server.fastmcp import FastMCP

# Import resources and tools
from resources import player, world
from tools import commands, messages, script_api

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger("mc-mcp-server")

# Load configuration
def load_config():
    try:
        with open("config/default.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load configuration: {e}")
        return {
            "server": {"host": "0.0.0.0", "port": 8080},
            "mcp": {"name": "Minecraft Assistant", "version": "1.0.0"},
            "auth": {"required": True, "token_expiry": 86400},
            "logging": {"level": "INFO"}
        }

# Handler for incoming Minecraft messages
async def handle_minecraft_message(client_id, message_type, message):
    if message_type == "PlayerMessage":
        sender = message.get("body", {}).get("sender", "")
        content = message.get("body", {}).get("message", "")
        logger.info(f"Player message from {sender}: {content}")
        
        # Process chat messages that start with specific prefixes
        if content.startswith("#"):
            # Command message
            command = content[1:].strip()
            if command.startswith("登录"):
                # Login command
                pass
            elif command.startswith("GPT"):
                # GPT chat command
                pass
            elif command.startswith("运行命令"):
                # Run command
                pass

async def setup_minecraft_server():
    # Load configuration
    config = load_config()
    
    # Create Minecraft server
    minecraft_server = MinecraftServer(config, handle_minecraft_message)
    return minecraft_server

# Create FastMCP server
def create_mcp_server(minecraft_server=None):
    # Load configuration
    config = load_config()
    
    # Create FastMCP server
    mcp_server = FastMCP(
        name=config.get("mcp", {}).get("name", "Minecraft Assistant"),
        dependencies=["asyncio", "websockets", "uuid", "mcp", "python-dotenv", "fastapi", "uvicorn", "pydantic"]
    )
    
    # Register tools
    @mcp_server.tool()
    async def execute_command(command: str) -> dict:
        """Execute a Minecraft command."""
        if minecraft_server:
            # If we have a minecraft server, use it
            client_id = mcp_server.get_context().client_id
            success = await minecraft_server.run_command(client_id, command)
            return {
                "success": success,
                "message": f"Command executed: {command}" if success else f"Failed to execute command: {command}"
            }
        else:
            # Otherwise use a placeholder
            return {
                "success": True,
                "message": f"Command executed: {command}"
            }
    
    @mcp_server.tool()
    async def send_message(message: str, target: str = None) -> dict:
        """Send a message to the game chat."""
        if minecraft_server:
            # If we have a minecraft server, use it
            client_id = mcp_server.get_context().client_id
            formatted_message = message.replace('"', '\\"')  # Escape double quotes
            
            if target:
                # Send a message to a specific player
                command = f'tellraw {target} {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
            else:
                # Send a message to all players
                command = f'tellraw @a {{"rawtext":[{{"text":"{formatted_message}"}}]}}'
            
            success = await minecraft_server.run_command(client_id, command)
            return {
                "success": success,
                "message": formatted_message,
                "target": target or "all"
            }
        else:
            # Otherwise use a placeholder
            return {
                "success": True,
                "message": message,
                "target": target or "all"
            }
    
    @mcp_server.tool()
    async def teleport_player(player_name: str, x: float, y: float, z: float, dimension: str = None) -> dict:
        """Teleport a player to specified coordinates."""
        if dimension:
            command = f"tp {player_name} {x} {y} {z} {dimension}"
        else:
            command = f"tp {player_name} {x} {y} {z}"
        
        return await execute_command(command)
    
    @mcp_server.tool()
    async def give_item(player_name: str, item: str, amount: int = 1, data: int = 0) -> dict:
        """Give an item to a player."""
        command = f"give {player_name} {item} {amount} {data}"
        return await execute_command(command)
    
    @mcp_server.tool()
    async def send_script_event(event_id: str, data: dict) -> dict:
        """Send a script event to the game."""
        if minecraft_server:
            # If we have a minecraft server, use it
            client_id = mcp_server.get_context().client_id
            # Format the data as JSON
            json_data = json.dumps(data).replace('"', '\\"')  # Escape double quotes
            
            # Send script event to the game
            success = await minecraft_server.send_script_event(client_id, event_id, json_data)
            return {
                "success": success,
                "event_id": event_id,
                "data": data
            }
        else:
            # Otherwise use a placeholder
            return {
                "success": True,
                "event_id": event_id,
                "data": data
            }
    
    @mcp_server.resource("minecraft://player/{player_name}")
    async def get_player_info(player_name: str) -> dict:
        """Get information about a player."""
        # In a real implementation, we would query the game
        # Here, we just return a placeholder
        return {
            "name": player_name,
            "position": {"x": 0, "y": 0, "z": 0},
            "health": 20,
            "level": 0,
            "gamemode": "survival"
        }
    
    @mcp_server.resource("minecraft://world")
    async def get_world_info() -> dict:
        """Get information about the current world."""
        # In a real implementation, we would query the game
        # Here, we just return a placeholder
        return {
            "name": "Minecraft World",
            "time": 0,
            "weather": "clear",
            "difficulty": "normal",
            "gamemode": "survival"
        }
    
    @mcp_server.resource("minecraft://world/block/{x}/{y}/{z}")
    async def get_block_info(x: int, y: int, z: int) -> dict:
        """Get information about a block at the specified coordinates."""
        # In a real implementation, we would query the game
        # Here, we just return a placeholder
        return {
            "position": {"x": x, "y": y, "z": z},
            "type": "unknown",
            "properties": {}
        }
    
    return mcp_server

async def run_both_servers():
    """Run both the Minecraft server and the MCP server."""
    try:
        # Start Minecraft server
        minecraft_server = await setup_minecraft_server()
        
        # Create MCP server with Minecraft server
        mcp_server = create_mcp_server(minecraft_server)
        
        # Start MCP server in a separate task
        mcp_task = asyncio.create_task(mcp_server.run(transport="stdio"))
        
        # Start Minecraft server
        minecraft_task = asyncio.create_task(minecraft_server.start())
        
        # Wait for both servers to complete
        await asyncio.gather(mcp_task, minecraft_task)
    except KeyboardInterrupt:
        logger.info("Shutting down servers")
    except Exception as e:
        logger.error(f"Error running servers: {e}", exc_info=True)
    finally:
        # Clean up
        if 'minecraft_server' in locals():
            await minecraft_server.stop()
        if 'mcp_task' in locals() and not mcp_task.done():
            mcp_task.cancel()
            try:
                await mcp_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    # Check if we should run both servers or just MCP server
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # Run both servers (Minecraft and MCP)
        asyncio.run(run_both_servers())
    else:
        # For client testing, we only run the MCP server 
        # with stdio transport (no Minecraft server integration)
        mcp_server = create_mcp_server()
        mcp_server.run(transport="stdio") 