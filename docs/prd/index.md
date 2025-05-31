# Minecraft MCP服务器文档索引

## 项目概述

Minecraft MCP服务器是一个连接Minecraft客户端与大语言模型(LLM)的WebSocket服务器，通过MCP标准实现智能交互。

## 文档目录

### 1. 项目需求文档

- [项目需求描述文档 (PRD)](pr.md) - 详细描述项目的核心功能、用户交互流程和验收标准

### 2. 技术规范文档

- [技术架构文档](technical_architecture.md) - 描述系统的整体架构、核心组件和技术栈
- [WebSocket通信规范](websocket_spec.md) - 定义客户端与服务器之间的WebSocket通信协议
- [MCP集成规范](mcp_integration.md) - 说明如何集成Model Context Protocol标准

### 3. 外部参考文档

- [MCP Python SDK](../MCP_PYTHON_SDK.md) - Model Context Protocol的Python实现参考

## 快速入门

1. 阅读[项目需求描述文档](pr.md)了解项目概况
2. 参考[技术架构文档](technical_architecture.md)了解系统设计
3. 查看[WebSocket通信规范](websocket_spec.md)了解通信协议
4. 学习[MCP集成规范](mcp_integration.md)了解LLM集成方式

## 开发指南

1. 安装依赖:
   ```
   pip install asyncio websockets uuid
   ```

2. 设置环境变量:
   ```
   export siliconflow_apikey=your_api_key
   ```

3. 运行服务器:
   ```
   python main_server.py
   ```

4. 连接Minecraft客户端到服务器(默认端口8080)

## 贡献指南

1. 遵循项目的代码风格和架构设计
2. 提交前确保代码通过测试
3. 更新相关文档以反映代码变更

## 版本历史

- v0.1: 基础WebSocket服务器和LLM集成
- v0.2: 完善命令系统和安全认证(当前版本) 