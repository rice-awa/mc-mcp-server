import json
import asyncio
import logging
import sys
from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mc-mcp-frontend")

# Create FastMCP server
mcp_server = FastMCP(
    name="Minecraft Assistant Frontend",
    description="Frontend server for Minecraft Assistant that exposes tools and resources",
    dependencies=["asyncio", "websockets", "uuid", "mcp", "python-dotenv", "fastapi", "uvicorn", "pydantic"]
)

# Backend communication
async def send_to_backend(request_type, **kwargs):
    """Send a request to the backend server via stdio"""
    request = {
        "client_id": "frontend",
        "request": {
            "type": request_type,
            **kwargs
        }
    }
    
    # Write to stdout
    sys.stdout.write(json.dumps(request) + "\n")
    sys.stdout.flush()
    
    # Read response from stdin
    response_line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
    if not response_line:
        logger.error("No response received from backend")
        return {"error": {"code": "backend_error", "message": "No response from backend"}}
    
    try:
        response = json.loads(response_line)
        return response.get("response", {})
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from backend: {e}")
        return {"error": {"code": "backend_error", "message": "Invalid response from backend"}}

# Register tools
@mcp_server.tool()
async def execute_command(command: str) -> dict:
    """Execute a Minecraft command."""
    response = await send_to_backend("tool", name="execute_command", parameters={"command": command})
    return response.get("result", {"error": "Failed to execute command"})

@mcp_server.tool()
async def send_message(message: str, target: str = None) -> dict:
    """Send a message to the game chat."""
    response = await send_to_backend("tool", name="send_message", 
                                    parameters={"message": message, "target": target})
    return response.get("result", {"error": "Failed to send message"})

@mcp_server.tool()
async def teleport_player(player_name: str, x: float, y: float, z: float, dimension: str = None) -> dict:
    """Teleport a player to specified coordinates."""
    response = await send_to_backend("tool", name="teleport_player", 
                                    parameters={
                                        "player_name": player_name,
                                        "x": x,
                                        "y": y,
                                        "z": z,
                                        "dimension": dimension
                                    })
    return response.get("result", {"error": "Failed to teleport player"})

# Register resources
@mcp_server.resource("minecraft://player/{player_name}")
async def get_player_info(player_name: str) -> dict:
    """Get information about a player."""
    response = await send_to_backend("resource", uri=f"minecraft://player/{player_name}")
    return response.get("data", {"error": "Failed to get player info"})

@mcp_server.resource("minecraft://world")
async def get_world_info() -> dict:
    """Get information about the current world."""
    response = await send_to_backend("resource", uri="minecraft://world")
    return response.get("data", {"error": "Failed to get world info"})

@mcp_server.resource("minecraft://world/block/{x}/{y}/{z}")
async def get_block_info(x: int, y: int, z: int) -> dict:
    """Get information about a block at the specified coordinates."""
    response = await send_to_backend("resource", uri=f"minecraft://world/block/{x}/{y}/{z}")
    return response.get("data", {"error": "Failed to get block info"})

if __name__ == "__main__":
    # Run MCP server with stdio transport
    mcp_server.run(transport="stdio") 