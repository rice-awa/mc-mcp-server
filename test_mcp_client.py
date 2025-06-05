#!/usr/bin/env python3
import asyncio
import json
import sys
import traceback
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters, types

async def test_mcp_client():
    """
    Simple test script to verify MCP client connection and tool usage.
    """
    print("Starting MCP client test...")
    
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python",  # Executable
        args=["main.py","--full"],  # Script to run - using mcp_only_server.py instead of main.py
        env=None,  # No additional environment variables
    )
    
    # Connect to the MCP server
    try:
        print("Connecting to MCP server...")
        async with stdio_client(server_params) as (read, write):
            print("Connected. Creating session...")
            async with ClientSession(read, write) as session:
                # Initialize the connection
                print("Initializing MCP connection...")
                await session.initialize()
                print("Connection initialized successfully!")
                
                # List available resources
                print("\nListing available resources:")
                try:
                    resources = await session.list_resources()
                    print(f"Resources: {resources}")
                    if hasattr(resources, "resources"):
                        for resource in resources.resources:
                            print(f"  - {resource.name}: {resource.description}")
                    else:
                        print("Resources list format not as expected. Raw data:", resources)
                except Exception as e:
                    print(f"Error listing resources: {e}")
                    traceback.print_exc()
                
                # List available tools
                print("\nListing available tools:")
                try:
                    tools = await session.list_tools()
                    print(f"Tools: {tools}")
                    if hasattr(tools, "tools"):
                        for tool in tools.tools:
                            print(f"  - {tool.name}: {tool.description}")
                    else:
                        print("Tools list format not as expected. Raw data:", tools)
                except Exception as e:
                    print(f"Error listing tools: {e}")
                    traceback.print_exc()
                
                # Test a tool: send_message
                print("\nTesting send_message tool...")
                try:
                    result = await session.call_tool("send_message", {"message": "Hello from MCP client test!"})
                    print(f"Tool result: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")
                except Exception as e:
                    print(f"Error calling tool: {e}")
                    traceback.print_exc()
                
                # Test a resource: get world info
                print("\nTesting minecraft://world resource...")
                try:
                    content, mime_type = await session.read_resource("minecraft://world")
                    print(f"Resource content: {content}")
                    print(f"Mime type: {mime_type}")
                except Exception as e:
                    print(f"Error reading resource: {e}")
                    traceback.print_exc()
                
                print("\nMCP client test completed.")
    except Exception as e:
        print(f"Error during MCP client test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_client())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)