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
from server.mcp_server import MCPServer
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
            "mcp": {"host": "0.0.0.0", "port": 8000, "enabled": True},
            "auth": {"required": True, "token_expiry": 86400},
            "logging": {"level": "INFO"}
        }

# 解析命令行参数
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Minecraft Agent 服务器")
    parser.add_argument("--full", action="store_true", help="运行完整服务器（Minecraft和Agent）")
    parser.add_argument("--mcp", action="store_true", help="启用MCP服务器")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，记录WebSocket数据包")
    parser.add_argument("--mcp-port", type=int, help="指定MCP服务器端口", default=8000)
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
        "列出工具包": list_tool_packages,
        "查看工具包": view_package_tools,
        "帮助": show_help
    }
    
    # 如果没有参数，显示帮助
    if not args:
        await show_help(client_id, sender, "", minecraft_server, agent_server)
        return
    
    # 查找并执行对应的测试命令处理器
    # 按照命令长度降序排序，确保先匹配最长的命令前缀
    sorted_prefixes = sorted(test_command_handlers.keys(), key=len, reverse=True)
    for test_prefix in sorted_prefixes:
        if args.startswith(test_prefix):
            test_args = args[len(test_prefix):].strip()
            await test_command_handlers[test_prefix](client_id, sender, test_args, minecraft_server, agent_server)
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
    
    # 提示可以使用工具包命令查看更多组织化的工具
    await minecraft_server.send_game_message(client_id, "提示: 使用 '#测试Agent 列出工具包' 可查看工具的分类")

async def list_tool_packages(client_id, sender, args, minecraft_server, agent_server):
    """列出可用工具包"""
    packages = agent_server.get_tool_packages()
    
    if not packages:
        await minecraft_server.send_game_message(client_id, "当前没有可用的工具包")
        return
        
    await minecraft_server.send_game_message(client_id, f"可用工具包列表 ({len(packages)}个):")
    for name, description in packages.items():
        await minecraft_server.send_game_message(client_id, f"- {name}: {description}")
    
    # 提示可以查看特定包的工具
    await minecraft_server.send_game_message(client_id, "提示: 使用 '#测试Agent 查看工具包 [包名]' 查看包中的工具")

async def view_package_tools(client_id, sender, args, minecraft_server, agent_server):
    """查看特定工具包中的工具"""
    if not args:
        await minecraft_server.send_game_message(client_id, "请指定要查看的工具包名称")
        await minecraft_server.send_game_message(client_id, "例如: #测试Agent 查看工具包 commands")
        return
    
    package_name = args.strip()
    tools = agent_server.get_package_tools(package_name)
    
    if not tools:
        await minecraft_server.send_game_message(client_id, f"工具包 '{package_name}' 不存在或没有工具")
        return
    
    await minecraft_server.send_game_message(client_id, f"工具包 '{package_name}' 中的工具 ({len(tools)}个):")
    
    for name, description in tools.items():
        # 提取描述的第一行作为简短描述
        first_line = next((line.strip() for line in description.split('\n') if line.strip()), "无描述")
        await minecraft_server.send_game_message(client_id, f"- {name}: {first_line}")
    
    # 提示可以查看特定工具的详情
    await minecraft_server.send_game_message(client_id, "提示: 使用 '#测试Agent 查看工具 [工具名]' 查看工具详情")

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
    
    # 从工具注册表中获取工具
    from server.utils.tools import tool_registry
    tool = tool_registry.get_tool(tool_name)
    
    if not tool:
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
        result = await tool.execute(**params)
        
        # 发送结果
        import json
        result_str = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
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
    
    # 从工具注册表中获取工具文档
    from server.utils.tools import tool_registry
    tool_doc = tool_registry.get_tool_doc(tool_name)
    
    if not tool_doc:
        await minecraft_server.send_game_message(client_id, f"找不到工具: {tool_name}")
        await minecraft_server.send_game_message(client_id, "使用 '#测试Agent 列出工具' 查看可用工具")
        return
    
    # 格式化描述
    formatted_desc = "\n".join([line.strip() for line in tool_doc.split('\n') if line.strip()])
    
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
    await minecraft_server.send_game_message(client_id, "- 列出工具包: 显示按功能分类的工具包")
    await minecraft_server.send_game_message(client_id, "- 查看工具包 [包名]: 查看指定工具包中的工具")
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
        from server.utils.tools import tool_registry
        
        # 导入工具模块 - 它们会自动注册到工具注册表
        import tools.commands
        import tools.messages
        import tools.script_api
        
        # 注册与工具注册表兼容的工具 - 这已经不需要了，工具自动注册
        # 但是保留这些导入以确保模块被加载
        
        logger.info(f"已导入工具模块，工具注册表中有 {len(tool_registry.get_all_tool_names())} 个工具")
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

def setup_mcp_server(minecraft_server=None):
    """设置并返回MCP服务器实例"""
    # 加载配置
    config = load_config()
    
    # 创建MCP服务器
    mcp_server = MCPServer(config, minecraft_server)
    
    logger.info("已创建MCP服务器")
    
    return mcp_server

async def run_all_servers(debug_mode=False, enable_mcp=None, mcp_port=None):
    """运行Minecraft服务器、Agent服务器和MCP服务器"""
    # 加载配置
    config = load_config()
    
    # 从配置中获取MCP设置（如果命令行参数未指定）
    if enable_mcp is None:
        enable_mcp = config.get("mcp", {}).get("enabled", False)
    
    if mcp_port is None:
        mcp_port = config.get("mcp", {}).get("port", 8000)
    
    mcp_host = config.get("mcp", {}).get("host", "0.0.0.0")
    mcp_transport = config.get("mcp", {}).get("transport", "sse")
    
    # 设置Minecraft服务器
    minecraft_server = await setup_minecraft_server(debug_mode)
    
    # 设置Agent服务器
    agent_server = setup_agent_server(minecraft_server)
    
    # 启动Minecraft服务器
    mc_server_task = asyncio.create_task(minecraft_server.start())
    
    # 设置MCP服务器（如果启用）
    mcp_server = None
    mcp_server_task = None
    
    if enable_mcp:
        try:
            # 导入必要的模块
            import mcp
            logger.info("已检测到MCP库，正在设置MCP服务器...")
            
            # 创建MCP服务器
            mcp_server = setup_mcp_server(minecraft_server)
            
            # 通过settings设置host和port
            mcp_server.mcp_server.settings.host = mcp_host
            mcp_server.mcp_server.settings.port = mcp_port
            
            # 使用线程启动MCP服务器，因为FastMCP的run方法会阻塞
            import threading
            mcp_thread = threading.Thread(
                target=lambda: mcp_server.run(transport=mcp_transport),
                daemon=True  # 使其成为守护线程，这样主程序退出时它会自动结束
            )
            mcp_thread.start()
            
            logger.info(f"MCP服务器启动中，地址: {mcp_host}:{mcp_port}，传输方式: {mcp_transport}")
            
            # 不再使用asyncio.create_task，因为已经使用线程启动了
            mcp_server_task = None
        except ImportError:
            logger.warning("未安装MCP库，无法启动MCP服务器")
        except Exception as e:
            logger.error(f"启动MCP服务器时出错: {e}", exc_info=True)
    
    # 等待服务器完成
    try:
        # 等待Minecraft服务器任务完成
        await mc_server_task
    except asyncio.CancelledError:
        logger.info("Minecraft服务器任务被取消")
    finally:
        # 我们不需要取消mcp_server_task，因为使用的是线程
        # 线程设置为daemon=True，主程序退出时会自动结束
        pass

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 设置文件日志
    log_file = setup_file_logging()
    
    # 加载配置
    config = load_config()
    
    try:
        # 确定是否启用MCP服务器
        # 如果通过命令行明确指定了--mcp，则使用命令行参数
        # 否则使用配置文件中的设置
        enable_mcp = args.mcp if args.mcp else config.get("mcp", {}).get("enabled", False)
        
        # 获取MCP端口（命令行参数优先）
        mcp_port = args.mcp_port if args.mcp_port != 8000 else config.get("mcp", {}).get("port", 8000)
        
        # 运行后端服务器
        logger.info("启动Minecraft Agent 服务器")
        logger.info(f"MCP服务器: {'启用' if enable_mcp else '禁用'}")
        if enable_mcp:
            logger.info(f"MCP服务器端口: {mcp_port}")
        
        asyncio.run(run_all_servers(
            debug_mode=args.debug,
            enable_mcp=enable_mcp,
            mcp_port=mcp_port
        ))
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.critical(f"服务器运行时出错: {e}", exc_info=True)
        sys.exit(1)