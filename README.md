# Minecraft MCP服务器文档索引

## 项目概述

Minecraft MCP服务器是一个集成系统，由两个核心组件组成：AIAgent(MCP-server)负责管理AI工具和处理LLM交互，以及基于WebSocket和脚本API的MC服务器负责处理游戏交互。系统支持两种请求路径：外部MCP客户端调用和游戏内聊天监听。

## 文档目录

### 1. 项目需求文档

- [项目需求描述文档 (PRD)](/docs/prd/pr.md) - 详细描述项目的核心功能、请求路径、用户交互流程和验收标准

### 2. 技术规范文档

- [技术架构文档](/docs/prd/technical_architecture.md) - 描述系统的整体架构、核心组件和技术栈
- [WebSocket通信规范](/docs/prd/websocket_spec.md) - 定义客户端与服务器之间的WebSocket通信协议和脚本API集成
- [MCP集成规范](/docs/prd/mcp_integration.md) - 说明如何集成Model Context Protocol标准和两种请求路径

### 3. 外部参考文档

- [MCP Python SDK](/docs/MCP_PYTHON_SDK.md) - Model Context Protocol的Python实现参考
- [Minecraft脚本API文档](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/) - Minecraft脚本API官方文档

## 系统组件

1. **AIAgent (MCP-server)** - 负责管理AI工具和处理LLM交互
2. **MC服务器** - 基于WebSocket和脚本API的服务器，处理游戏交互

## 请求路径

1. **外部MCP客户端路径** - 外部MCP客户端通过AIAgent与Minecraft交互
2. **游戏内聊天路径** - 玩家通过游戏内聊天触发AIAgent

## 快速入门

1. 阅读[项目需求描述文档](/docs/prd/pr.md)了解项目概况
2. 参考[技术架构文档](/docs/prd/technical_architecture.md)了解系统设计
3. 查看[WebSocket通信规范](/docs/prd/websocket_spec.md)了解通信协议和脚本API集成
4. 学习[MCP集成规范](/docs/prd/mcp_integration.md)了解LLM集成方式和请求路径

## 项目结构规范

```
mc-mcp-server/
├── server/
│   ├── __init__.py
│   ├── mc_server.py       # WebSocket服务器实现
│   ├── mcp_server.py      # MCP服务器实现
│   └── utils/
│       ├── __init__.py
│       ├── auth.py        # 认证相关工具
│       ├── llm.py         # 大语言模型调用工具
│       └── logging.py     # 日志工具
│
├── resources/             # MCP资源定义
│   ├── __init__.py
│   ├── player.py
│   └── world.py
├── tools/                 # MCP工具定义
│   ├── __init__.py
│   ├── commands.py
│   └── messages.py
├── config/                # 配置文件
│   ├── default.json
│   └── production.json
├── tests/                 # 测试目录
│   ├── __init__.py
│   ├── test_mc_server.py
│   └── test_mcp_server.py
├── docs/                  # 文档目录
├── main.py                # 主入口文件
├── requirements.txt       # 依赖声明
└── README.md              # 项目说明

```

## 开发指南

1. 安装依赖:
   ```
   pip install asyncio websockets uuid mcp
   ```

2. 设置环境变量:
   ```
   export siliconflow_apikey=your_api_key
   ```

3. 启动MC服务器:
   ```
   # 标准模式
   python main.py --full
   
   # 调试模式（记录WebSocket数据包）
   python main.py --full --debug
   ```

4. 启动AIAgent:
   ```
   python ai_agent.py
   ```

5. 连接Minecraft客户端到MC服务器(默认端口8080)

## 调试与日志

服务器提供了调试模式和增强的日志功能，帮助开发者诊断和解决问题：

- **调试模式**：使用 `--debug` 参数启动服务器，记录所有WebSocket数据包
- **日志文件**：日志自动保存在 `logs` 目录下
  - 主服务器日志：`logs/server_YYYYMMDD-HHMMSS.log`
  - WebSocket数据包日志：`logs/packets/packets_YYYYMMDD-HHMMSS.log`

详细信息请参阅 [调试模式和日志功能文档](/docs/DEBUG_MODE.md)。

## 贡献指南

1. 遵循项目的代码风格和架构设计
2. 提交前确保代码通过测试
3. 更新相关文档以反映代码变更

## 版本历史


## 许可信息
- 本项目以[MIT](./LICENSE)开源
- 其他项目许可证见[LICENSES](/licenses/mcp-python-sdk-LICENSE)