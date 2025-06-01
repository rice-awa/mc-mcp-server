# Minecraft MCP服务器开发规范

## 概述

本文档定义了Minecraft MCP服务器项目的开发规范，包含使用Python开发WebSocket服务器和MCP服务器时的注意事项，以及确保开发符合PRD文档边界需求的指南。


## Python编码规范

### 1. 命名约定

- **类名**：使用驼峰命名法（CamelCase）
- **函数和变量**：使用小写字母加下划线（snake_case）
- **常量**：使用大写字母加下划线（UPPER_SNAKE_CASE）
- **私有方法和属性**：使用前导下划线（_private_method）

### 2. 代码组织

- 每个模块应当专注于单一功能
- 相关功能应分组到同一个模块中
- 使用类型注解提高代码可读性和IDE支持

```python
async def handle_connection(websocket: websockets.WebSocketServerProtocol) -> None:
    """处理WebSocket连接

    Args:
        websocket: WebSocket连接对象
    """
    client_id = str(uuid.uuid4())
    try:
        # 处理连接逻辑
        pass
    except Exception as e:
        logger.error(f"连接处理错误: {e}")
    finally:
        # 清理资源
        pass
```

### 3. 异步编程规范

- 本项目使用异步完成

- 使用`async/await`语法进行异步编程
- 避免在异步函数中使用阻塞操作
- 使用`asyncio.gather`处理并发任务
- 使用适当的异常处理机制捕获异步操作的异常

```python
async def process_messages(client_id: str, websocket: websockets.WebSocketServerProtocol) -> None:
    try:
        async for message in websocket:
            task = asyncio.create_task(handle_message(client_id, message))
            # 可以选择等待任务完成或使用回调
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"处理消息错误: {e}")
```

### 4. 日志规范

- 使用Python标准日志库
- 定义不同级别的日志：DEBUG, INFO, WARNING, ERROR, CRITICAL
- 在关键点记录操作和状态信息
- 记录异常信息和堆栈跟踪

```python
import logging

logger = logging.getLogger("mc-mcp-server")

# 配置日志
def setup_logging():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

## WebSocket服务器开发规范

### 1. 连接管理

- 使用`websockets`库实现WebSocket服务器
- 每个连接分配唯一标识符
- 实现心跳机制确保连接活跃
- 优雅处理连接断开和重连

```python
# WebSocket服务器配置
websocket_config = {
    'ping_interval': 30,       # 心跳间隔（秒）
    'ping_timeout': 15,        # 心跳超时（秒）
    'close_timeout': 15,       # 关闭超时（秒）
    'max_size': 10 * 1024 * 1024,  # 最大消息大小（10MB）
    'max_queue': 32,           # 最大队列长度
}

async def start_server(ip: str, port: int):
    async with websockets.serve(handle_connection, ip, port, **websocket_config):
        logger.info(f"WebSocket服务器已启动，监听 {ip}:{port}")
        await asyncio.Future()  # 保持服务器运行
```

### 2. 消息处理

- 使用JSON格式处理消息
- 定义清晰的消息类型和结构
- 使用模式验证确保消息格式正确
- 实现超时处理防止长时间阻塞

```python
async def handle_message(client_id: str, raw_message: str) -> None:
    try:
        # 解析JSON消息
        message = json.loads(raw_message)
        
        # 验证消息格式
        if not validate_message(message):
            await send_error(client_id, "无效的消息格式")
            return
            
        # 根据消息类型分发处理
        message_type = message.get("type")
        if message_type == "chat":
            await handle_chat_message(client_id, message)
        elif message_type == "command":
            await handle_command_message(client_id, message)
        else:
            await send_error(client_id, f"未知的消息类型: {message_type}")
    except json.JSONDecodeError:
        await send_error(client_id, "无效的JSON格式")
    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        await send_error(client_id, "服务器内部错误")
```

### 3. 错误处理

- 定义标准错误响应格式
- 区分客户端错误和服务器错误
- 记录详细的错误日志
- 向客户端返回友好的错误消息

```python
async def send_error(client_id: str, error_message: str, error_code: int = 400) -> None:
    """发送错误响应到客户端

    Args:
        client_id: 客户端ID
        error_message: 错误消息
        error_code: 错误代码
    """
    error_response = {
        "type": "error",
        "code": error_code,
        "message": error_message
    }
    await send_message(client_id, error_response)
    logger.error(f"客户端 {client_id} 错误: {error_message}")
```

### 4. 安全措施

- 实现基于密钥的认证机制
- 使用TLS/SSL加密WebSocket连接（WSS）
- 实施请求限流防止DDoS攻击
- 验证所有客户端输入

```python
async def authenticate_client(websocket, message):
    """验证客户端身份

    Args:
        websocket: WebSocket连接
        message: 包含认证信息的消息

    Returns:
        bool: 认证是否成功
    """
    auth_key = message.get("key")
    if not auth_key:
        await websocket.send(json.dumps({"type": "error", "message": "缺少认证密钥"}))
        return False
        
    # 验证密钥
    if not verify_auth_key(auth_key):
        await websocket.send(json.dumps({"type": "error", "message": "无效的认证密钥"}))
        return False
        
    # 认证成功，生成会话令牌
    token = generate_session_token()
    await websocket.send(json.dumps({"type": "auth_success", "token": token}))
    return True
```

## MCP服务器开发规范

### 1. 资源定义

- 资源URI遵循`minecraft://{resource_type}/{resource_id}`格式
- 每个资源提供明确的类型注解和文档字符串
- 资源函数应处理异常并返回标准化结果
- 资源缓存策略应根据资源类型定制

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Minecraft Assistant")

@mcp.resource("minecraft://player/{player_name}")
async def get_player(player_name: str) -> dict:
    """获取指定玩家的信息
    
    通过服务器脚本API获取特定玩家的详细信息。
    
    Args:
        player_name (str): 要查询信息的玩家名称，使用'current'表示当前交互的玩家
    
    Returns:
        dict: 包含玩家信息的字典，包括生命值、位置、物品栏等信息
    
    Raises:
        ValueError: 当玩家名称无效时
        ResourceNotFoundError: 当玩家不存在时
    """
    try:
        # 获取玩家信息的实现
        player_info = await fetch_player_info(player_name)
        return player_info
    except PlayerNotFoundError:
        raise ResourceNotFoundError(f"玩家 {player_name} 不存在")
    except Exception as e:
        logger.error(f"获取玩家信息时出错: {e}")
        raise
```

### 2. 工具实现

- 工具函数应有明确的功能描述
- 参数和返回值使用类型注解
- 实现参数验证和错误处理
- 考虑工具的权限控制

```python
@mcp.tool()
async def run_command(command: str) -> str:
    """在Minecraft中执行命令
    
    执行Minecraft命令并返回结果。
    
    Args:
        command (str): 要执行的Minecraft命令字符串，不包含前导斜杠
    
    Returns:
        str: 命令执行后的结果消息
    
    Raises:
        ValueError: 当命令格式无效时
        PermissionError: 当命令执行权限不足时
        CommandExecutionError: 当命令执行失败时
    """
    # 验证命令
    if not command or not isinstance(command, str):
        raise ValueError("命令必须是非空字符串")
        
    # 检查命令安全性
    if not is_safe_command(command):
        raise PermissionError(f"命令 '{command}' 不允许执行")
    
    try:
        # 执行命令
        result = await execute_minecraft_command(command)
        return result
    except Exception as e:
        logger.error(f"执行命令 '{command}' 时出错: {e}")
        raise CommandExecutionError(f"命令执行失败: {str(e)}")
```

### 3. MCP集成

- 使用FastMCP创建服务器实例
- 实现适当的生命周期管理
- 定义清晰的应用上下文
- 配置合适的认证机制

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from mcp.server.fastmcp import FastMCP

# 创建MCP服务器
mcp = FastMCP("Minecraft Assistant")

@dataclass
class AppContext:
    """应用上下文类，管理应用级别的共享资源"""
    websocket_manager: WebSocketManager
    # 其他共享资源...

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """管理应用生命周期"""
    # 初始化资源
    websocket_manager = WebSocketManager()
    await websocket_manager.start()
    
    try:
        yield AppContext(websocket_manager=websocket_manager)
    finally:
        # 清理资源
        await websocket_manager.shutdown()

# 使用生命周期管理
mcp.lifespan(app_lifespan)
```

### 4. 与WebSocket服务器集成

- 定义清晰的通信协议
- 实现异常处理和重试逻辑
- 优化消息传递效率
- 确保两个服务器之间的安全通信

```python
class WebSocketManager:
    """管理与Minecraft客户端的WebSocket连接"""
    
    def __init__(self):
        self.active_connections = {}
        self.lock = asyncio.Lock()
    
    async def start(self):
        """启动WebSocket管理器"""
        logger.info("WebSocket管理器启动")
    
    async def shutdown(self):
        """关闭所有连接并清理资源"""
        async with self.lock:
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"关闭连接 {client_id} 时出错: {e}")
        logger.info("WebSocket管理器已关闭")
    
    async def send_to_minecraft(self, client_id: str, message: dict) -> None:
        """发送消息到Minecraft客户端
        
        Args:
            client_id: 客户端ID
            message: 要发送的消息
            
        Raises:
            ConnectionError: 当连接不存在或已关闭时
        """
        async with self.lock:
            if client_id not in self.active_connections:
                raise ConnectionError(f"客户端 {client_id} 不存在或已断开连接")
            
            connection = self.active_connections[client_id]
            try:
                await connection.send(json.dumps(message))
            except Exception as e:
                logger.error(f"发送消息到客户端 {client_id} 时出错: {e}")
                raise ConnectionError(f"发送消息失败: {str(e)}")
```

## PRD文档边界遵循规范

### 1. 功能边界

- 严格按照PRD文档中定义的核心功能开发
- 先实现最小可行产品(MVP)，再逐步添加高级功能
- 每个功能应有对应的单元测试和集成测试
- 功能开发顺序应遵循项目时间线

### 2. 请求路径实现

- 完整实现两种请求路径：外部MCP客户端路径和游戏内聊天路径
- 确保路径之间的隔离和独立运行
- 优化每种路径的性能和响应时间
- 实现健壮的错误处理和回退机制

### 3. 安全与认证

- 实现PRD中定义的安全认证机制
- 确保密钥和令牌的安全存储和传输
- 实施适当的访问控制和权限验证
- 防止常见的安全漏洞（如注入攻击、DDoS等）

### 4. 性能要求

- 满足PRD中的低延迟要求（<500ms）
- 支持多用户并发连接
- 实现适当的资源限制和负载均衡
- 监控系统性能并进行必要的优化

### 5. 扩展性设计

- 遵循模块化设计原则
- 确保代码可配置性和可扩展性
- 为未来扩展做好准备
- 实现插件化架构支持自定义扩展



### 1. 日志与监控

- 实现全面的日志记录
- 设置监控系统跟踪性能指标
- 建立告警机制发现问题
- 定期审查日志和性能数据

### 2. 错误处理与恢复

- 实现全局异常处理机制
- 设计故障恢复策略
- 实现优雅降级机制
- 创建系统状态健康检查

## 总结

本开发规范提供了开发Minecraft MCP服务器项目的全面指南，包括Python编码规范、WebSocket服务器和MCP服务器开发注意事项，以及确保符合PRD文档边界需求的方法。遵循这些规范将有助于创建高质量、可维护的代码，并确保项目的顺利进行。 