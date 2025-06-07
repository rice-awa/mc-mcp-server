# MCP客户端与服务器通信示例

本文档说明如何使用外部MCP客户端与Minecraft MCP服务器进行通信，以实现与Minecraft游戏的交互。

## 服务器配置

Minecraft MCP服务器通过SSE（Server-Sent Events）通信方式对外提供服务，默认配置如下：

```json
{
  "mcp": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8000,
    "transport": "sse"
  }
}
```

## 启动服务器

有两种方式启动MCP服务器：

1. **通过配置文件**：在`config/default.json`中设置`mcp.enabled`为`true`，然后正常启动服务器。

2. **通过命令行参数**：使用`--mcp`参数启动服务器，可以通过`--mcp-port`指定端口。

```bash
# 启动完整服务器，包括MCP服务器
python main.py --full --mcp

# 指定MCP服务器端口
python main.py --full --mcp --mcp-port 6000
```

## MCP客户端使用示例

### Python客户端

以下是一个使用Python MCP客户端与服务器通信的示例：

```python
from mcp.client import MCPClient

async def main():
    # 连接到MCP服务器
    client = await MCPClient.connect("http://localhost:8000")
    
    # 发送消息到游戏
    result = await client.use_tool("send_message", {
        "message": "你好，Minecraft世界！"
    })
    print(f"发送消息结果: {result}")
    
    # 执行命令
    result = await client.use_tool("execute_command", {
        "command": "say 这是一个测试命令"
    })
    print(f"执行命令结果: {result}")
    
    # 获取玩家信息
    player_info = await client.get_resource("minecraft://player/steve")
    print(f"玩家信息: {player_info}")
    
    # 获取世界信息
    world_info = await client.get_resource("minecraft://world")
    print(f"世界信息: {world_info}")
    
    # 传送玩家
    result = await client.use_tool("teleport_player", {
        "player_name": "steve",
        "x": 100,
        "y": 64,
        "z": 100
    })
    print(f"传送结果: {result}")
    
    # 关闭连接
    await client.close()

# 运行示例
import asyncio
asyncio.run(main())
```

### 使用curl测试

您也可以使用curl命令行工具测试MCP服务器：

```bash
# 获取世界信息
curl -X GET "http://localhost:8000/resources/minecraft%3A%2F%2Fworld"

# 执行工具
curl -X POST "http://localhost:8000/tools/execute_command" \
  -H "Content-Type: application/json" \
  -d '{"command": "say Hello from curl!"}'
```

## 可用资源和工具

### 资源

MCP服务器提供以下资源：

1. `minecraft://player/{player_name}` - 获取玩家信息
2. `minecraft://world` - 获取当前世界信息
3. `minecraft://world/block/{x}/{y}/{z}` - 获取特定坐标处的方块信息

### 工具

MCP服务器提供以下工具：

1. `execute_command` - 执行Minecraft命令
   - 参数：`command` (字符串) - 要执行的命令
   - 参数：`client_id` (字符串，可选) - 客户端ID

2. `send_message` - 发送消息到游戏聊天
   - 参数：`message` (字符串) - 要发送的消息
   - 参数：`client_id` (字符串，可选) - 客户端ID
   - 参数：`target` (字符串，可选) - 消息目标，默认为所有人

3. `teleport_player` - 传送玩家到指定坐标
   - 参数：`player_name` (字符串) - 玩家名称
   - 参数：`x` (浮点数) - X坐标
   - 参数：`y` (浮点数) - Y坐标
   - 参数：`z` (浮点数) - Z坐标
   - 参数：`client_id` (字符串，可选) - 客户端ID
   - 参数：`dimension` (字符串，可选) - 维度名称

## 错误处理

MCP服务器将返回标准的错误响应：

```json
{
  "error": {
    "code": "error_code",
    "message": "错误描述"
  }
}
```

常见错误码包括：

- `invalid_request` - 请求格式无效
- `not_found` - 资源或工具未找到
- `server_error` - 服务器内部错误
- `minecraft_error` - Minecraft服务器错误 