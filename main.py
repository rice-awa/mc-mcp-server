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
        # 获取脚本所在的目录路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config", "default.json")
        
        logger.info(f"尝试加载配置文件: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
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
            
            elif command.startswith("测试MCP"):
                # 测试MCP
                test_command = command[5:].strip()
                if test_command == "列出工具":
                    # 获取MCP服务器实例
                    mcp_server = minecraft_server.mcp_server
                    if mcp_server:
                        # 获取工具列表
                        tools = mcp_server.get_tools()
                        # 发送工具列表到游戏
                        await minecraft_server.send_game_message(client_id, f"可用工具列表 ({len(tools)}个):")
                        for name, description in tools.items():
                            # 提取描述的第一行作为简短描述
                            first_line = description.split('\n')[0].strip()
                            if not first_line:  # 如果第一行为空，尝试获取下一行
                                for line in description.split('\n'):
                                    if line.strip():
                                        first_line = line.strip()
                                        break
                            
                            if not first_line:  # 如果仍然为空
                                first_line = "无描述"
                                
                            await minecraft_server.send_game_message(client_id, f"- {name}: {first_line}")
                    else:
                        await minecraft_server.send_game_message(client_id, "MCP服务器未初始化")

                elif test_command == "列出资源":
                    # 获取MCP服务器实例
                    mcp_server = minecraft_server.mcp_server
                    if mcp_server:
                        # 获取资源列表
                        resources = mcp_server.get_resources()
                        # 发送资源列表到游戏
                        await minecraft_server.send_game_message(client_id, f"可用资源列表 ({len(resources)}个):")
                        for uri_pattern, description in resources.items():
                            # 提取描述的第一行作为简短描述
                            first_line = description.split('\n')[0].strip()
                            if not first_line:  # 如果第一行为空，尝试获取下一行
                                for line in description.split('\n'):
                                    if line.strip():
                                        first_line = line.strip()
                                        break
                            
                            if not first_line:  # 如果仍然为空
                                first_line = "无描述"
                                
                            await minecraft_server.send_game_message(client_id, f"- {uri_pattern}: {first_line}")
                    else:
                        await minecraft_server.send_game_message(client_id, "MCP服务器未初始化")
                
                elif test_command.startswith("使用工具"):
                    # 使用指定的工具
                    tool_args = test_command[4:].strip().split(' ', 1)
                    if len(tool_args) >= 1:
                        tool_name = tool_args[0]
                        mcp_server = minecraft_server.mcp_server
                        if mcp_server and tool_name in mcp_server.tools:
                            await minecraft_server.send_game_message(client_id, f"正在尝试使用工具: {tool_name}")
                            try:
                                # 构建简单参数
                                params = {}
                                if len(tool_args) > 1 and tool_args[1]:
                                    # 尝试解析参数，格式为 key=value
                                    param_parts = tool_args[1].split()
                                    for part in param_parts:
                                        if '=' in part:
                                            k, v = part.split('=', 1)
                                            params[k] = v
                                # 获取到的参数
                                await minecraft_server.send_game_message(client_id, f"获取到的参数: {params}")
                                
                                # 调用工具
                                tool_func = mcp_server.tools[tool_name]
                                result = await tool_func(client_id=client_id, **params)
                                
                                # 发送结果
                                result_str = json.dumps(result, ensure_ascii=False, indent=2)
                                await minecraft_server.send_game_message(client_id, f"工具执行结果: {result_str}")
                            except Exception as e:
                                logger.error(f"执行工具时出错: {e}", exc_info=True)
                                await minecraft_server.send_game_message(client_id, f"执行工具时出错: {str(e)}")
                        else:
                            await minecraft_server.send_game_message(client_id, f"找不到工具: {tool_name}")
                            await minecraft_server.send_game_message(client_id, "使用 '#测试MCP 列出工具' 查看可用工具")
                    else:
                        await minecraft_server.send_game_message(client_id, "请指定要使用的工具名称")
                
                elif test_command.startswith("查看工具"):
                    # 查看特定工具的详细信息
                    tool_name = test_command[4:].strip()
                    if not tool_name:
                        await minecraft_server.send_game_message(client_id, "请指定要查看的工具名称")
                        await minecraft_server.send_game_message(client_id, "例如: #测试MCP 查看工具 execute_command")
                    else:
                        mcp_server = minecraft_server.mcp_server
                        if mcp_server and tool_name in mcp_server.tools:
                            # 获取工具描述
                            tool_func = mcp_server.tools[tool_name]
                            description = tool_func.__doc__ or "无描述"
                            # 格式化描述
                            formatted_desc = "\n".join([line.strip() for line in description.split('\n') if line.strip()])
                            
                            # 发送工具详细信息
                            await minecraft_server.send_game_message(client_id, f"工具详细信息: {tool_name}")
                            await minecraft_server.send_game_message(client_id, "描述:")
                            # 分段发送描述，避免消息过长
                            desc_lines = formatted_desc.split('\n')
                            for line in desc_lines:
                                if line.strip():
                                    await minecraft_server.send_game_message(client_id, line.strip())
                        else:
                            await minecraft_server.send_game_message(client_id, f"找不到工具: {tool_name}")
                            await minecraft_server.send_game_message(client_id, "使用 '#测试MCP 列出工具' 查看可用工具")
                
                elif test_command == "帮助":
                    # 显示帮助信息
                    await minecraft_server.send_game_message(client_id, "MCP测试命令帮助:")
                    await minecraft_server.send_game_message(client_id, "- 列出工具: 显示所有可用的MCP工具")
                    await minecraft_server.send_game_message(client_id, "- 列出资源: 显示所有可用的MCP资源")
                    await minecraft_server.send_game_message(client_id, "- 查看工具 [工具名]: 查看特定工具的详细描述")
                    await minecraft_server.send_game_message(client_id, "- 使用工具 [工具名] [参数]: 测试指定的工具")
                    await minecraft_server.send_game_message(client_id, "  例如: #测试MCP 使用工具 send_message message=你好")
                    await minecraft_server.send_game_message(client_id, "- 帮助: 显示此帮助信息")
                
                else:
                    # 未知测试命令
                    await minecraft_server.send_game_message(client_id, f"未知测试命令: {test_command}")
                    await minecraft_server.send_game_message(client_id, "使用 '#测试MCP 帮助' 查看可用命令")

            else:
                # 未知命令
                await minecraft_server.send_game_message(client_id, f"未知命令: {command}")
                await minecraft_server.send_game_message(client_id, "可用命令: 登录, GPT, 运行命令, 测试MCP")

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
    
    # 添加mcp_server属性，初始值为None
    minecraft_server.mcp_server = None
    
    return minecraft_server

def setup_mcp_server(minecraft_server=None):
    """设置并返回MCP服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建MCP服务器
    mcp_server = MCPServer(config, minecraft_server)
    
    # 如果有Minecraft服务器实例，设置相互引用
    if minecraft_server:
        minecraft_server.mcp_server = mcp_server
    
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
        
        # 创建MCP服务器并设置相互引用
        mcp_server = setup_mcp_server(minecraft_server)
        # 确保minecraft_server引用mcp_server
        minecraft_server.mcp_server = mcp_server
        
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