# Minecraft MCP服务器 WebSocket通信规范

## 概述

本文档定义了Minecraft MCP服务器与Minecraft客户端之间的WebSocket通信协议规范。该协议基于JSON格式的消息交换，支持事件订阅、命令执行和消息传递等功能。

## 连接建立

### 连接URL

```
ws://{server_ip}:{port}
```

默认端口为`8080`。

### 连接流程

1. 客户端发起WebSocket连接请求
2. 服务器接受连接并发送欢迎消息
3. 客户端订阅所需事件（如PlayerMessage）
4. 建立双向通信通道

## 消息格式

所有消息均采用JSON格式，包含header和body两个主要部分。

### 基本消息结构

```json
{
  "header": {
    "requestId": "string",      // UUID格式的请求标识符
    "messagePurpose": "string", // 消息目的
    "version": number,          // 协议版本号
    "EventName": "string"       // 事件名称
  },
  "body": {
    // 根据messagePurpose不同而变化
  }
}
```

## 事件订阅

### 订阅事件消息

客户端通过发送订阅消息来监听特定游戏事件。

```json
{
  "body": {
    "eventName": "PlayerMessage" // 要订阅的事件名称
  },
  "header": {
    "requestId": "uuid-string",
    "messagePurpose": "subscribe",
    "version": 1,
    "EventName": "commandRequest"
  }
}
```

支持的事件类型包括：
- `PlayerMessage`: 玩家聊天消息
- `ScriptEventReceived`: 脚本事件接收

## 命令请求

### 聊天消息命令

向游戏内发送聊天消息。

```json
{
  "body": {
    "origin": {
      "type": "say"
    },
    "commandLine": "tellraw @a {\"rawtext\":[{\"text\":\"§a消息内容\"}]}",
    "version": 1
  },
  "header": {
    "requestId": "uuid-string",
    "messagePurpose": "commandRequest",
    "version": 1,
    "EventName": "commandRequest"
  }
}
```

### 游戏命令执行

执行Minecraft游戏命令。

```json
{
  "body": {
    "origin": {
      "type": "player"
    },
    "commandLine": "命令内容",
    "version": 17039360
  },
  "header": {
    "requestId": "uuid-string",
    "messagePurpose": "commandRequest",
    "version": 1,
    "EventName": "commandRequest"
  }
}
```

### 脚本事件命令

通过脚本事件发送数据。

```json
{
  "body": {
    "origin": {
      "type": "player"
    },
    "commandLine": "scriptevent 消息ID 内容",
    "version": 17039360
  },
  "header": {
    "requestId": "uuid-string",
    "messagePurpose": "commandRequest",
    "version": 1,
    "EventName": "commandRequest"
  }
}
```

## 事件响应

### 玩家消息事件

当玩家在游戏中发送消息时，服务器会接收到以下格式的事件：

```json
{
  "body": {
    "sender": "玩家名称",
    "message": "消息内容"
  },
  "header": {
    "eventName": "PlayerMessage"
  }
}
```

### 命令响应

执行命令后的响应：

```json
{
  "body": {
    "statusCode": 0,      // 0表示成功
    "statusMessage": ""   // 错误时包含错误信息
  },
  "header": {
    "requestId": "uuid-string"
  }
}
```

## LLM集成消息格式

服务器与LLM API之间的通信采用以下格式：

### 服务器到客户端的LLM响应

```json
{
  "type": "content",      // 可以是 "content", "reasoning", "error"
  "content": "消息内容"
}
```

响应类型说明：
- `content`: LLM的最终回复内容
- `reasoning`: LLM的思考过程（当启用思考链输出时）
- `error`: 错误信息

### 思考过程特殊标记

思考过程使用特殊标记进行包装：

- 开始标记: `|think-start|`
- 结束标记: `|think-end|`

## 安全认证

### 登录流程

1. 客户端发送登录命令: `#登录 密钥`
2. 服务器验证密钥
3. 成功时生成并存储令牌
4. 向客户端返回登录成功/失败消息

### 命令权限控制

除登录命令外，所有命令均需验证令牌有效性。未登录用户的命令请求会被拒绝。

## 错误处理

### 错误响应格式

```json
{
  "type": "error",
  "content": "错误: 错误描述"
}
```

常见错误类型：
- 认证失败
- LLM API调用失败
- 命令格式错误
- 连接超时

## 示例交互流程

### 完整的LLM对话流程

1. 客户端连接到WebSocket服务器
2. 服务器发送欢迎消息
3. 客户端订阅PlayerMessage事件
4. 客户端发送登录命令: `#登录 密钥`
5. 服务器验证并返回成功消息
6. 客户端发送GPT聊天命令: `GPT 聊天 你好，请介绍一下自己`
7. 服务器调用LLM API
8. 服务器实时返回LLM思考过程（如启用）
9. 服务器返回LLM最终回复
10. 客户端展示回复内容

## 扩展性考虑

本协议设计支持未来扩展，可通过以下方式进行：

1. 增加新的事件类型
2. 扩展消息体字段
3. 提高版本号以支持新功能

## 兼容性说明

本协议设计兼容Minecraft Bedrock Edition的WebSocket接口，同时支持MCP标准的LLM交互。 