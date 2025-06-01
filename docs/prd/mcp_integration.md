# MCP集成规范

## 概述

本文档描述了Minecraft MCP服务器如何集成Model Context Protocol (MCP)标准，实现两种请求路径：外部MCP客户端调用和游戏内聊天监听。系统由AIAgent(MCP-server)和基于WebSocket和脚本API的MC服务器组成。

## MCP简介

Model Context Protocol (MCP) 是一个标准化协议，允许应用程序以标准化的方式为大语言模型(LLM)提供上下文，将提供上下文的关注点与实际的LLM交互分离。

## 集成架构

```
                                  ┌─────────────────┐
                                  │ 外部MCP客户端    │
                                  └────────┬────────┘
                                           │ MCP
                                           ▼
┌────────────────┐    WebSocket    ┌────────────────┐    MCP    ┌────────────────┐
│  Minecraft客户端 │<--------------->│  MC服务器      │<--------->│  AIAgent       │<---┐
└────────────────┘                 └────────────────┘           └────────────────┘    │
                                                                        │             │
                                                                        ▼             │
                                                              ┌────────────────┐      │
                                                              │    LLM API     │------┘
                                                              └────────────────┘
```

## 请求路径

### 1. 外部MCP客户端路径

外部MCP客户端通过AIAgent与Minecraft交互：

1. 外部MCP客户端使用MCP协议连接到AIAgent
2. AIAgent处理请求并通过WebSocket与MC服务器通信
3. MC服务器通过脚本API与Minecraft客户端交互
4. 结果通过相同路径返回给外部MCP客户端

### 2. 游戏内聊天路径

玩家通过游戏内聊天触发AIAgent：

1. 玩家在Minecraft中发送聊天消息
2. MC服务器通过WebSocket和脚本API监听这些消息
3. MC服务器将特定命令转发给AIAgent
4. AIAgent处理请求并通过LLM API获取响应
5. 响应通过MC服务器返回到游戏内

## MCP资源定义

### 1. 资源类型

在AIAgent中，我们定义以下MCP资源：

- **游戏状态资源**: 通过脚本API提供Minecraft游戏当前状态的信息
- **玩家资源**: 通过脚本API提供关于玩家的信息
- **世界资源**: 通过脚本API提供关于游戏世界的信息

### 2. 资源URI模式

资源采用以下URI模式：

```
minecraft://{resource_type}/{resource_id}
```

例如：
- `minecraft://player/current` - 当前玩家信息
- `minecraft://world/status` - 世界状态信息

## MCP工具定义


### 1. 命令工具

允许LLM通过脚本API执行Minecraft命令：

```python
@mcp.tool()
def run_command(command: str) -> str:
    """在Minecraft中执行命令
    
    此函数允许执行Minecraft命令，并返回命令的执行结果。
    
    Args:
        command (str): 要执行的Minecraft命令字符串，不包含前导斜杠
    
    Returns:
        str: 命令执行后的结果消息
    """
    # 通过MC服务器和脚本API执行命令
    return "命令执行结果"
```

### 2. 消息工具

允许LLM向游戏内发送消息：

```python
@mcp.tool()
def send_message(message: str) -> None:
    """向游戏内发送消息
    
    将指定消息发送到Minecraft游戏内聊天频道，所有玩家可见。
    
    Args:
        message (str): 要发送到游戏内的文本消息，支持Minecraft格式代码
    
    Returns:
        None: 此函数没有返回值
    """
    # 通过MC服务器和脚本API发送消息
```

### 3. 脚本工具

允许LLM执行脚本事件：

```python
@mcp.tool()
def run_script(script_id: str, content: str) -> None:
    """执行脚本事件
    
    执行预定义的脚本事件，允许LLM触发复杂的游戏内交互。
    
    Args:
        script_id (str): 要执行的脚本标识符
        content (str): 提供给脚本的JSON格式参数字符串
    
    Returns:
        None: 此函数没有返回值
    """
    # 通过MC服务器和脚本API执行脚本
```

### 4. 游戏信息获取工具

允许LLM获取游戏内信息：

```python
@mcp.tool()
def get_game_info(info_type: str) -> dict:
    """获取游戏内信息
    
    获取特定类型的游戏内信息，如玩家状态、世界信息等。
    
    Args:
        info_type (str): 要获取的信息类型，如'player_stats'、'world_time'等
    
    Returns:
        dict: 包含请求信息的字典，格式根据info_type不同而变化
    """
    # 通过MC服务器和脚本API获取游戏信息
    return {"type": info_type, "data": {...}}
```

## MCP提示模板

### 系统提示模板

```
你是一个Minecraft游戏助手，可以帮助玩家解决问题、提供建议和执行命令。

可用工具:
- run_command: 执行Minecraft命令
- send_message: 发送游戏内消息
- run_script: 执行脚本事件
- get_game_info: 获取游戏内信息

请保持友好和专业的态度。回答应简洁明了，适合在游戏内阅读。
```

## 数据流程

### 1. 外部MCP客户端路径数据流

```
外部MCP客户端 -> MCP请求 -> AIAgent -> WebSocket消息 -> MC服务器 -> 脚本API -> Minecraft客户端
Minecraft客户端 -> 脚本API -> MC服务器 -> WebSocket响应 -> AIAgent -> MCP响应 -> 外部MCP客户端
```

### 2. 游戏内聊天路径数据流

```
Minecraft客户端 -> 聊天消息 -> 脚本API -> MC服务器 -> 命令解析 -> AIAgent -> LLM请求
LLM API -> LLM响应 -> AIAgent -> 响应处理 -> MC服务器 -> WebSocket消息 -> Minecraft客户端
```

## 示例交互

### 示例1: 玩家请求游戏帮助

```
玩家: "GPT 聊天 如何制作钻石镐?"

MCP请求:
{
  "prompt": "如何制作钻石镐?",
  "context": {...}
}

LLM响应:
{
  "reasoning": "我需要告诉玩家制作钻石镐的具体步骤和所需材料...",
  "content": "制作钻石镐需要3个钻石和2根木棍。将它们在工作台上按'T'形排列，顶部一行放3个钻石，中间格放1根木棍，最底部中间格放1根木棍。"
}
```

### 示例2: 执行游戏命令

```
玩家: "GPT 聊天 给我一个钻石剑"

MCP请求:
{
  "prompt": "给我一个钻石剑",
  "tools": ["run_command"],
  "context": {...}
}

LLM响应:
{
  "reasoning": "玩家想要一个钻石剑，我可以使用run_command工具执行give命令...",
  "tool_calls": [
    {
      "name": "run_command",
      "parameters": {
        "command": "give @p diamond_sword 1"
      }
    }
  ],
  "content": "已经给你一把钻石剑了，请查看你的物品栏。"
}
```

### 示例3: 外部MCP客户端请求

```
外部MCP客户端请求:
{
  "prompt": "在玩家周围生成一圈火焰",
  "tools": ["run_script"]
}

AIAgent处理:
- 调用run_script工具
- MC服务器通过脚本API执行脚本
- 返回执行结果

MCP响应:
{
  "content": "已在玩家周围生成火焰圈",
  "tool_results": [...]
}
```

## AIAgent配置

### 1. 服务器初始化

```python
from mcp.server.fastmcp import FastMCP

# 创建MCP服务器
mcp = FastMCP("Minecraft Assistant")

# 添加资源和工具
@mcp.resource("minecraft://player/{player_name}")
def get_player(player_name: str) -> dict:
    """获取指定玩家的信息
    
    通过服务器脚本API获取特定玩家的详细信息。
    
    Args:
        player_name (str): 要查询信息的玩家名称，使用'current'表示当前交互的玩家
    
    Returns:
        dict: 包含玩家信息的字典，包括生命值、位置、物品栏等信息
    """
    # 通过MC服务器和脚本API获取玩家信息
    return {"name": player_name, "health": 20, "level": 30}

@mcp.tool()
def run_command(command: str) -> str:
    """在Minecraft中执行命令
    
    执行Minecraft命令并返回结果。
    
    Args:
        command (str): 要执行的Minecraft命令字符串，不包含前导斜杠
    
    Returns:
        str: 命令执行后的结果消息
    """
    # 通过MC服务器和脚本API执行命令
    return "命令执行结果"
```

### 2. MC服务器集成

```python
async def handle_mcp_request(prompt: str, conversation: list) -> dict:
    """处理来自游戏内或外部客户端的MCP请求
    
    创建并发送MCP请求到AIAgent，然后处理响应。
    
    Args:
        prompt (str): 用户/玩家的提问或请求文本
        conversation (list): 之前的对话历史，用于维持上下文连续性
    
    Returns:
        dict: AIAgent的响应，包含文本内容和可能的工具调用结果
    """
    # 创建MCP请求
    mcp_request = {
        "prompt": prompt,
        "resources": ["minecraft://player/current"],
        "tools": ["run_command", "send_message", "get_game_info"]
    }
    
    # 发送MCP请求并获取响应
    response = await mcp.process_request(mcp_request)
    
    # 处理响应
    return response
    
# WebSocket消息处理
async def handle_websocket_message(message: dict) -> None:
    """处理来自Minecraft客户端的WebSocket消息
    
    解析从游戏内发送的WebSocket消息，识别聊天命令并处理MCP请求。
    
    Args:
        message (dict): 来自WebSocket连接的消息对象，包含消息类型、玩家和内容等信息
    
    Returns:
        None: 此函数不返回值，但会通过WebSocket将响应发送回游戏内
    """
    if is_chat_command(message):
        # 处理游戏内聊天命令
        response = await handle_mcp_request(extract_prompt(message), conversation)
        await send_to_minecraft(response)
```

## 安全考虑

1. **命令限制**: 限制LLM可以执行的命令范围，防止危险操作
2. **资源访问控制**: 控制LLM可以访问的游戏资源
3. **用户认证**: 确保只有授权用户可以使用LLM功能
4. **外部MCP客户端验证**: 验证外部MCP客户端的身份和权限

## 未来扩展

1. **更多资源类型**: 添加更多游戏内资源类型的支持
2. **高级工具**: 实现更复杂的游戏交互工具
3. **自定义提示模板**: 允许用户自定义LLM提示模板
4. **多模型支持**: 支持多种LLM模型的无缝切换
5. **脚本API扩展**: 利用更多脚本API功能增强交互能力 