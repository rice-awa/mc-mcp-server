"""
Minecraft MCP 服务器的入口文件

此文件作为程序的入口点，负责初始化和启动服务器，
具体实现细节均位于server目录下。
"""
import os
import json
import asyncio
import logging
import argparse
import sys
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

# 解析命令行参数
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Minecraft MCP 服务器")
    parser.add_argument("--full", action="store_true", help="运行完整服务器（Minecraft和MCP）")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，记录WebSocket数据包")
    return parser.parse_args()

# 设置日志文件
def setup_file_logging():
    """设置日志文件"""
    # 使用增强的日志工具
    from server.utils.logging import setup_daily_rotating_file_handler
    
    # 设置日志目录
    log_dir = "logs"
    
    # 为根记录器添加文件处理程序
    root_logger = logging.getLogger()
    log_file = setup_daily_rotating_file_handler(root_logger, log_dir, "server")
    
    logger.info(f"日志将保存到: {log_file}")
    return log_file

# Minecraft消息处理函数
async def handle_minecraft_message(client_id, event_type, message, minecraft_server=None):
    """处理来自Minecraft的消息
    
    Args:
        client_id (str): 客户端标识符
        event_type (str): 事件类型
        message (dict): 消息内容
        minecraft_server (MinecraftServer, optional): Minecraft服务器实例
    """
    if event_type == "PlayerMessage":
        sender = message.get("body", {}).get("sender", "")
        content = message.get("body", {}).get("message", "")
        logger.info(f"收到玩家 {sender} 的消息: {content}")
        
        # 处理以特定前缀开头的聊天消息
        if content.startswith("#") and minecraft_server:
            # 命令消息
            command = content[1:].strip()
            if command.startswith("登录"):
                # 登录命令
                await minecraft_server.send_game_message(client_id, f"收到登录请求，用户: {sender}")
                # 这里可以添加登录逻辑
            elif command.startswith("GPT"):
                # GPT聊天命令
                query = command[3:].strip()
                if query:
                    pass
 
            elif command.startswith("运行命令"):
                # 运行Minecraft命令
                mc_command = command[4:].strip()
                if mc_command:
                    logger.info(f"执行Minecraft命令: {mc_command}")
                    await minecraft_server.run_command(client_id, mc_command)
                else:
                    await minecraft_server.send_game_message(client_id, "请提供要运行的命令")
            else:
                # 未知命令
                await minecraft_server.send_game_message(client_id, f"未知命令: {command}")

async def setup_minecraft_server(debug_mode=False):
    """设置并返回Minecraft服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建一个临时处理函数，稍后会被更新
    temp_handler = lambda client_id, event_type, message: None
    
    # 创建Minecraft服务器
    minecraft_server = MinecraftServer(config, temp_handler, debug_mode=debug_mode)
    
    # 创建一个包含minecraft_server的闭包函数
    async def handler_with_server(client_id, event_type, message):
        await handle_minecraft_message(client_id, event_type, message, minecraft_server)
    
    # 更新处理函数
    minecraft_server.event_handler = handler_with_server
    
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

async def run_both_servers(debug_mode=False):
    """运行Minecraft服务器和MCP服务器"""
    try:
        # 启动Minecraft服务器
        minecraft_server = await setup_minecraft_server(debug_mode)
        
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
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志文件
    log_file = setup_file_logging()
    
    # 打印启动信息
    logger.info(f"正在启动Minecraft MCP服务器...")
    logger.info(f"调试模式: {'启用' if args.debug else '禁用'}")
    logger.info(f"服务器模式: {'完整模式' if args.full else 'MCP模式'}")
    
    if args.full:
        # 运行两个服务器（Minecraft和MCP）
        asyncio.run(run_both_servers(debug_mode=args.debug))
    else:
        # 用于客户端测试，我们只运行MCP服务器
        # 使用stdio传输（无Minecraft服务器集成）
        mcp_server = setup_mcp_server()
        asyncio.run(mcp_server.run(transport="stdio")) 