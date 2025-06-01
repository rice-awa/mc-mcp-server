### 项目需求描述文档 (PRD)

# Minecraft MCP服务器

## 项目概述

Minecraft MCP服务器是一个集成系统，由两个核心组件组成：

1. **AIAgent (MCP-server)**: 负责管理AI工具和处理LLM的输入输出，通过MCP（Model Context Protocol）标准实现
2. **MC服务器**: 基于WebSocket和脚本API的服务器，专注于处理Minecraft游戏交互

该项目实现了以下核心功能：

1. 通过WebSocket协议与Minecraft客户端建立实时通信
2. 利用Minecraft脚本API获取游戏内信息
3. 使用MCP标准处理LLM的输入输出
4. 支持两种请求路径：外部MCP客户端调用和游戏内聊天监听
5. 提供游戏内聊天、命令执行和脚本事件处理功能
6. 支持LLM思考过程的实时展示

## 请求路径

系统支持两种主要的请求路径：

### 1. 外部MCP客户端路径

外部MCP客户端通过AIAgent与Minecraft交互：
- 外部MCP客户端向AIAgent发送请求
- AIAgent处理请求并通过WebSocket与Minecraft客户端交互
- Minecraft客户端通过WebSocket返回结果给AIAgent
- AIAgent将结果返回给外部MCP客户端

### 2. 游戏内聊天路径

玩家通过游戏内聊天触发AIAgent：
- 玩家在游戏内发送聊天消息
- MC服务器通过WebSocket监听这些聊天消息
- MC服务器将消息转发给AIAgent
- AIAgent处理消息并通过LLM API获取响应
- AIAgent将响应返回给MC服务器
- MC服务器通过WebSocket将响应发送回游戏内

## 核心功能需求

### 1. MC服务器（游戏交互层）

- 在指定IP和端口上启动WebSocket服务器
- 集成Minecraft脚本API获取游戏内信息
- 处理客户端连接、消息接收和发送
- 维护连接状态和会话信息
- 支持多客户端并发连接

### 2. Minecraft客户端通信

- 订阅Minecraft游戏事件（如玩家消息）
- 向游戏内发送聊天消息
- 执行Minecraft命令
- 通过脚本事件指令发送数据
- 利用脚本API获取游戏内状态信息

### 3. AIAgent (MCP-server)

- 实现MCP标准接口
- 管理MCP资源和工具
- 处理LLM请求和响应
- 提供上下文管理功能
- 执行工具调用

### 4. LLM集成

- 连接到LLM API（如DeepSeek-R1、GPT-4o等）
- 发送用户提示并接收模型响应
- 支持流式输出，实时显示LLM回复
- 可选显示LLM思考过程

### 5. 安全认证（次优先级）

- 实现基于密钥的登录机制
- 生成和验证会话令牌
- 限制未认证用户的功能访问

### 6. 会话管理

- 支持上下文历史记录的开启/关闭
- 保存和清理对话历史
- 管理连接的唯一标识符(UUID)

## 用户交互流程

### 外部MCP客户端流程

1. 外部MCP客户端连接到AIAgent
2. AIAgent通过WebSocket连接到Minecraft客户端
3. 外部MCP客户端发送请求给AIAgent
4. AIAgent处理请求并通过WebSocket与Minecraft交互
5. AIAgent将结果返回给外部MCP客户端

### 游戏内聊天流程

1. 用户通过Minecraft客户端连接到MC服务器
2. 服务器发送欢迎消息，包含连接信息
3. 用户通过游戏内聊天输入特定命令（如"#登录"、"GPT 聊天"等）
4. MC服务器将命令转发给AIAgent
5. AIAgent处理请求并返回结果
6. 服务器验证用户权限并处理相应请求
7. 对于LLM请求，服务器将实时返回模型响应到游戏内聊天

## 命令系统

系统支持以下命令：

| 命令 | 功能描述 |
|------|---------|
| #登录 | 使用密钥验证用户身份 |
| GPT 聊天 | 向LLM发送消息并获取回复 |
| GPT 保存 | 保存当前对话历史 |
| GPT 上下文 | 开启/关闭上下文历史记录 |
| 运行命令 | 在Minecraft中执行命令 |
| GPT 脚本 | 执行LLM生成的脚本 |

## 技术规格

### 环境要求

- Python 3.7+
- 依赖库：asyncio, websockets, uuid, mcp
- 环境变量：API密钥和URL
- Minecraft Bedrock Edition支持脚本API

### 性能要求

- 支持多用户并发连接
- 低延迟消息处理（<500ms）
- 稳定的长时间运行能力

### 扩展性

- 模块化设计，便于添加新功能
- 支持多种LLM模型切换
- 可配置的系统参数
- 插件化架构支持自定义扩展

## 未来扩展计划

1. 添加更多LLM模型支持
2. 实现用户权限分级系统
3. 增强脚本API集成功能
4. 添加数据分析和日志记录功能
5. 开发Web管理界面
6. 支持更多脚本API功能

## 项目时间线

- 阶段1：基础WebSocket服务器和LLM集成（已完成）
- 阶段2：完善命令系统和安全认证（进行中）
- 阶段3：脚本API集成和AIAgent实现
- 阶段4：性能优化和稳定性测试
- 阶段5：文档完善和开源发布

## 验收标准

1. MC服务器能稳定运行并处理多客户端连接
2. 脚本API能正确获取游戏内信息
3. 两种请求路径（外部MCP客户端和游戏内聊天）均能正常工作
4. 所有命令功能正常工作
5. LLM响应准确且实时显示
6. 安全认证系统有效防止未授权访问
7. 系统在长时间运行中保持稳定