"""
Minecraft Agent 服务器的入口文件

此文件作为程序的入口点，负责初始化和启动服务器，
具体实现细节均位于server目录下。
"""
import os
import json
import asyncio
import logging
import argparse
import sys
import subprocess
from dotenv import load_dotenv

from server.mc_server import MinecraftServer
from server.agent_server import AgentServer
from server.utils.logging import setup_logging

# 加载环境变量
load_dotenv()

# 设置日志
setup_logging()
logger = logging.getLogger("mc-agent-server")

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
            "agent": {"name": "Minecraft Assistant", "version": "1.0.0"},
            "auth": {"required": True, "token_expiry": 86400},
            "logging": {"level": "INFO"}
        }

# 解析命令行参数
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Minecraft Agent 服务器")
    parser.add_argument("--full", action="store_true", help="运行完整服务器（Minecraft和Agent）")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，记录WebSocket数据包")
    parser.add_argument("--frontend", action="store_true", help="启动前端MCP服务器")
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
    if event_type != "PlayerMessage" or not minecraft_server:
        return
    
    sender = message.get("body", {}).get("sender", "")
    content = message.get("body", {}).get("message", "")
    logger.info(f"收到玩家 {sender} 的消息: {content}")
    
    # 命令前缀检查
    if not content.startswith("#"):
        return
    
    # 提取命令内容，移除前缀'#'
    command = content[1:].strip()
    
    # 命令处理器字典
    command_handlers = {
        "登录": handle_login_command,
        "GPT": handle_gpt_command,
        "运行命令": handle_run_command,
        "测试Agent": handle_test_agent_command
    }
    
    # 查找并执行对应的命令处理器
    for prefix, handler in command_handlers.items():
        if command.startswith(prefix):
            cmd_args = command[len(prefix):].strip()
            await handler(client_id, sender, cmd_args, minecraft_server)
            return
    
    # 没有找到匹配的命令
    await minecraft_server.send_game_message(client_id, f"未知命令: {command}")
    await minecraft_server.send_game_message(client_id, f"可用命令: {', '.join(command_handlers.keys())}")

async def handle_login_command(client_id, sender, args, minecraft_server):
    """处理登录命令"""
    await minecraft_server.send_game_message(client_id, f"收到登录请求，用户: {sender}")
    # 这里可以添加登录逻辑

async def handle_gpt_command(client_id, sender, args, minecraft_server):
    """处理GPT聊天命令"""
    if args:
        # 这里添加GPT聊天逻辑
        pass
    else:
        await minecraft_server.send_game_message(client_id, "请提供GPT查询内容")

async def handle_run_command(client_id, sender, args, minecraft_server):
    """处理运行Minecraft命令"""
    if args:
        logger.info(f"执行Minecraft命令: {args}")
        await minecraft_server.run_command(client_id, args)
    else:
        await minecraft_server.send_game_message(client_id, "请提供要运行的命令")

async def handle_test_agent_command(client_id, sender, args, minecraft_server):
    """处理测试Agent命令"""
    agent_server = minecraft_server.agent_server
    if not agent_server:
        await minecraft_server.send_game_message(client_id, "Agent服务器未初始化")
        return
    
    # 测试Agent子命令处理器
    test_command_handlers = {
        "列出工具": list_tools,
        "列出资源": list_resources,
        "使用工具": use_tool,
        "查看工具": view_tool,
        "帮助": show_help
    }
    
    # 如果没有参数，显示帮助
    if not args:
        await show_help(client_id, sender, "", minecraft_server, agent_server)
        return
    
    # 查找并执行对应的测试命令处理器
    for test_prefix, test_handler in test_command_handlers.items():
        if args.startswith(test_prefix):
            test_args = args[len(test_prefix):].strip()
            await test_handler(client_id, sender, test_args, minecraft_server, agent_server)
            return
    
    # 没有找到匹配的测试命令
    await minecraft_server.send_game_message(client_id, f"未知测试命令: {args}")
    await minecraft_server.send_game_message(client_id, "使用 '#测试Agent 帮助' 查看可用命令")

async def list_tools(client_id, sender, args, minecraft_server, agent_server):
    """列出可用工具"""
    tools = agent_server.get_tools()
    await minecraft_server.send_game_message(client_id, f"可用工具列表 ({len(tools)}个):")
    for name, description in tools.items():
        # 提取描述的第一行作为简短描述
        first_line = next((line.strip() for line in description.split('\n') if line.strip()), "无描述")
        await minecraft_server.send_game_message(client_id, f"- {name}: {first_line}")

async def list_resources(client_id, sender, args, minecraft_server, agent_server):
    """列出可用资源"""
    resources = agent_server.get_resources()
    await minecraft_server.send_game_message(client_id, f"可用资源列表 ({len(resources)}个):")
    for uri_pattern, description in resources.items():
        # 提取描述的第一行作为简短描述
        first_line = next((line.strip() for line in description.split('\n') if line.strip()), "无描述")
        await minecraft_server.send_game_message(client_id, f"- {uri_pattern}: {first_line}")

async def use_tool(client_id, sender, args, minecraft_server, agent_server):
    """使用指定的工具"""
    if not args:
        await minecraft_server.send_game_message(client_id, "请指定要使用的工具名称")
        return
    
    # 提取工具名称和参数
    parts = args.split(None, 1)
    tool_name = parts[0]
    
    if tool_name not in agent_server.tools:
        await minecraft_server.send_game_message(client_id, f"找不到工具: {tool_name}")
        await minecraft_server.send_game_message(client_id, "使用 '#测试Agent 列出工具' 查看可用工具")
        return
    
    await minecraft_server.send_game_message(client_id, f"正在尝试使用工具: {tool_name}")
    
    try:
        # 解析参数
        params = {"client_id": client_id}
        if len(parts) > 1:
            param_str = parts[1]
            # 使用更智能的参数解析，支持引号内的空格
            import re
            # 匹配key=value模式，同时支持带引号的值
            pattern = r'(\w+)=(?:"([^"]*)"|(\'([^\']*)\')|([^"\'\s][^\s]*))'
            matches = re.findall(pattern, param_str)
            for match in matches:
                key = match[0]
                # 取出值，优先处理引号中的值
                value = match[1] or match[3] or match[4]
                params[key] = value
        
        await minecraft_server.send_game_message(client_id, f"获取到的参数: {params}")
        
        # 调用工具
        tool_func = agent_server.tools[tool_name]
        result = await tool_func(**params)
        
        # 发送结果
        result_str = json.dumps(result, ensure_ascii=False, indent=2)
        await minecraft_server.send_game_message(client_id, f"工具执行结果: {result_str}")
    except Exception as e:
        logger.error(f"执行工具时出错: {e}", exc_info=True)
        await minecraft_server.send_game_message(client_id, f"执行工具时出错: {str(e)}")

async def view_tool(client_id, sender, args, minecraft_server, agent_server):
    """查看特定工具的详细信息"""
    if not args:
        await minecraft_server.send_game_message(client_id, "请指定要查看的工具名称")
        await minecraft_server.send_game_message(client_id, "例如: #测试Agent 查看工具 execute_command")
        return
    
    tool_name = args.strip()
    if tool_name not in agent_server.tools:
        await minecraft_server.send_game_message(client_id, f"找不到工具: {tool_name}")
        await minecraft_server.send_game_message(client_id, "使用 '#测试Agent 列出工具' 查看可用工具")
        return
    
    # 获取工具描述
    tool_func = agent_server.tools[tool_name]
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

async def show_help(client_id, sender, args, minecraft_server, agent_server):
    """显示帮助信息"""
    await minecraft_server.send_game_message(client_id, "Agent测试命令帮助:")
    await minecraft_server.send_game_message(client_id, "- 列出工具: 显示所有可用的Agent工具")
    await minecraft_server.send_game_message(client_id, "- 列出资源: 显示所有可用的Agent资源")
    await minecraft_server.send_game_message(client_id, "- 查看工具 [工具名]: 查看特定工具的详细描述")
    await minecraft_server.send_game_message(client_id, "- 使用工具 [工具名] [参数]: 测试指定的工具")
    await minecraft_server.send_game_message(client_id, "  例如: #测试Agent 使用工具 execute_command command=\"say 你好世界\"")
    await minecraft_server.send_game_message(client_id, "- 帮助: 显示此帮助信息")

async def setup_minecraft_server(debug_mode=False):
    """设置并返回Minecraft服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建一个临时处理函数，稍后会被更新
    temp_handler = lambda client_id, event_type, message: None
    
    # 创建Minecraft服务器
    minecraft_server = MinecraftServer(
        config=config,
        event_handler=temp_handler,
        debug_mode=debug_mode
    )
    
    # 创建真正的处理函数，现在可以引用minecraft_server
    async def handler_with_server(client_id, event_type, message):
        await handle_minecraft_message(client_id, event_type, message, minecraft_server)
    
    # 更新处理函数
    minecraft_server.event_handler = handler_with_server
    
    return minecraft_server

def setup_agent_server(minecraft_server=None):
    """设置并返回Agent服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建Agent服务器
    agent_server = AgentServer(config, minecraft_server)
    
    # 如果Minecraft服务器存在，设置其Agent服务器引用
    if minecraft_server:
        minecraft_server.agent_server = agent_server
    
    # 加载工具和资源
    logger.info("正在加载Agent工具和资源...")
    
    # 动态导入工具和资源模块
    try:
        # 导入工具
        import tools.commands
        import tools.messages
        import tools.script_api
        
        # 注册工具
        tools.commands.register_tools(agent_server)
        tools.messages.register_tools(agent_server)
        tools.script_api.register_tools(agent_server)
        
        logger.info("已导入并注册工具模块")
    except ImportError as e:
        logger.warning(f"无法导入工具模块: {e}")
    except Exception as e:
        logger.error(f"注册工具时出错: {e}", exc_info=True)
    
    try:
        # 导入资源
        import resources.player
        import resources.world
        
        # 注册资源
        resources.player.register_resources(agent_server)
        resources.world.register_resources(agent_server)
        
        logger.info("已导入并注册资源模块")
    except ImportError as e:
        logger.warning(f"无法导入资源模块: {e}")
    except Exception as e:
        logger.error(f"注册资源时出错: {e}", exc_info=True)
    
    return agent_server

async def run_frontend_server():
    """启动前端MCP服务器作为子进程"""
    logger.info("启动前端MCP服务器...")
    
    # 获取当前脚本的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_script = os.path.join(script_dir, "mcp_frontend_server.py")
    
    # 启动前端服务器进程
    process = await asyncio.create_subprocess_exec(
        sys.executable, frontend_script,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    logger.info(f"前端MCP服务器已启动，PID: {process.pid}")
    
    # 设置通信处理
    async def handle_frontend_output():
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            try:
                # 解析前端发送的请求
                message = json.loads(line.decode("utf-8"))
                client_id = message.get("client_id", "frontend")
                request = message.get("request", {})
                
                # 处理请求
                logger.debug(f"收到前端请求: {request}")
                # 这里可以处理前端请求
                
                # 发送响应
                response = {"client_id": client_id, "response": {"success": True}}
                process.stdin.write((json.dumps(response) + "\n").encode("utf-8"))
                await process.stdin.drain()
                
            except json.JSONDecodeError as e:
                logger.error(f"无效的前端消息: {e}")
    
    # 监听前端错误输出
    async def handle_frontend_error():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            logger.error(f"前端错误: {line.decode('utf-8').strip()}")
    
    # 启动通信处理任务
    asyncio.create_task(handle_frontend_output())
    asyncio.create_task(handle_frontend_error())
    
    return process

async def run_both_servers(debug_mode=False):
    """运行Minecraft服务器和Agent服务器"""
    # 设置Minecraft服务器
    minecraft_server = await setup_minecraft_server(debug_mode)
    
    # 设置Agent服务器
    agent_server = setup_agent_server(minecraft_server)
    
    # 启动Minecraft服务器
    await minecraft_server.start()
    
    # 运行Agent服务器
    await agent_server.run(transport="stdio")

async def run_backend_server(debug_mode=False):
    """运行后端服务器，与前端通信"""
    # 设置Minecraft服务器
    minecraft_server = await setup_minecraft_server(debug_mode)
    
    # 设置Agent服务器
    agent_server = setup_agent_server(minecraft_server)
    
    # 启动Minecraft服务器
    await minecraft_server.start()
    
    # 启动前端服务器
    frontend_process = await run_frontend_server()
    
    try:
        # 处理前端请求
        while True:
            # 从stdin读取前端请求
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            try:
                # 解析请求
                message = json.loads(line)
                client_id = message.get("client_id", "frontend")
                request = message.get("request", {})
                
                # 处理请求
                response = await agent_server.handle_agent_request(client_id, request)
                
                # 发送响应
                response_message = {
                    "client_id": client_id,
                    "response": response
                }
                sys.stdout.write(json.dumps(response_message) + "\n")
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                logger.error(f"无效的请求: {e}")
                sys.stdout.write(json.dumps({
                    "client_id": "error",
                    "response": {
                        "error": {
                            "code": "invalid_request",
                            "message": f"Invalid JSON: {str(e)}"
                        }
                    }
                }) + "\n")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"处理请求时出错: {e}", exc_info=True)
                sys.stdout.write(json.dumps({
                    "client_id": "error",
                    "response": {
                        "error": {
                            "code": "server_error",
                            "message": str(e)
                        }
                    }
                }) + "\n")
                sys.stdout.flush()
                
    finally:
        # 关闭前端进程
        if frontend_process.returncode is None:
            frontend_process.terminate()
            await frontend_process.wait()
        
        # 关闭服务器
        await minecraft_server.stop()
        await agent_server.close_all_conversations()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 设置文件日志
    log_file = setup_file_logging()
    
    try:
        if args.frontend:
            # 仅启动前端MCP服务器
            logger.info("仅启动前端MCP服务器")
            import mcp_frontend_server
        else:
            # 运行后端服务器
            logger.info("启动后端服务器")
            asyncio.run(run_backend_server(args.debug))
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.critical(f"服务器运行时出错: {e}", exc_info=True)
        sys.exit(1)