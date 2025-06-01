"""
Minecraft MCP 服务器的入口文件

此文件作为程序的入口点，负责初始化和启动服务器，
具体实现细节均位于server目录下。
"""
import os
import json
import asyncio
import logging
from dotenv import load_dotenv

from server.mc_server import MinecraftServer
from server.mcp_server import MCPServer
from server.utils.logging import setup_logging

# 加载环境变量
load_dotenv()

# 设置日志
setup_logging()
logger = logging.getLogger("mc-mcp-server")

# 加载配置文件
def load_config():
    """加载服务器配置文件"""
    try:
        with open("config/default.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"无法加载配置文件: {e}")
        return {
            "server": {"host": "0.0.0.0", "port": 8080},
            "mcp": {"name": "Minecraft Assistant", "version": "1.0.0"},
            "auth": {"required": True, "token_expiry": 86400},
            "logging": {"level": "INFO"}
        }

# Minecraft消息处理函数
async def handle_minecraft_message(client_id, message_type, message):
    """处理来自Minecraft的消息"""
    if message_type == "PlayerMessage":
        sender = message.get("body", {}).get("sender", "")
        content = message.get("body", {}).get("message", "")
        logger.info(f"收到玩家 {sender} 的消息: {content}")
        
        # 处理以特定前缀开头的聊天消息
        if content.startswith("#"):
            # 命令消息
            command = content[1:].strip()
            if command.startswith("登录"):
                # 登录命令
                pass
            elif command.startswith("GPT"):
                # GPT聊天命令
                pass
            elif command.startswith("运行命令"):
                # 运行命令
                pass

async def setup_minecraft_server():
    """设置并返回Minecraft服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建Minecraft服务器
    minecraft_server = MinecraftServer(config, handle_minecraft_message)
    return minecraft_server

def setup_mcp_server(minecraft_server=None):
    """设置并返回MCP服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建MCP服务器
    mcp_server = MCPServer(config, minecraft_server)
    
    # 加载并注册资源
    from resources import player, world
    player.register_resources(mcp_server)
    world.register_resources(mcp_server)
    
    # 加载并注册工具
    from tools import commands, messages, script_api
    commands.register_tools(mcp_server)
    messages.register_tools(mcp_server)
    script_api.register_tools(mcp_server)
    
    return mcp_server

async def run_both_servers():
    """运行Minecraft服务器和MCP服务器"""
    try:
        # 启动Minecraft服务器
        minecraft_server = await setup_minecraft_server()
        
        # 创建MCP服务器
        mcp_server = setup_mcp_server(minecraft_server)
        
        # 在单独的任务中启动MCP服务器
        mcp_task = asyncio.create_task(mcp_server.run(transport="stdio"))
        
        # 启动Minecraft服务器
        minecraft_task = asyncio.create_task(minecraft_server.start())
        
        # 等待两个服务器完成
        await asyncio.gather(mcp_task, minecraft_task)
    except KeyboardInterrupt:
        logger.info("正在关闭服务器")
    except Exception as e:
        logger.error(f"运行服务器时出错: {e}", exc_info=True)
    finally:
        # 清理资源
        if 'minecraft_server' in locals():
            await minecraft_server.stop()
        if 'mcp_task' in locals() and not mcp_task.done():
            mcp_task.cancel()
            try:
                await mcp_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    # 检查是否应该运行两个服务器或仅运行MCP服务器
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # 运行两个服务器（Minecraft和MCP）
        asyncio.run(run_both_servers())
    else:
        # 用于客户端测试，我们只运行MCP服务器
        # 使用stdio传输（无Minecraft服务器集成）
        mcp_server = setup_mcp_server()
        asyncio.run(mcp_server.run(transport="stdio")) 