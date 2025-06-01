# 调试模式和日志功能

## 概述

Minecraft MCP 服务器提供了调试模式和增强的日志功能，帮助开发者诊断和解决问题。本文档介绍如何使用这些功能。

## 调试模式

调试模式允许记录和查看所有 WebSocket 数据包，包括发送和接收的消息。

### 启用调试模式

使用 `--debug` 参数启动服务器：

```bash
# 启动完整服务器（Minecraft和MCP）并启用调试模式
python main.py --full --debug

# 仅启动MCP服务器并启用调试模式
python main.py --debug
```

### 调试模式功能

启用调试模式后，系统将：

1. 在控制台实时显示所有 WebSocket 数据包（彩色显示）
   - 接收的数据包显示为青色
   - 发送的数据包显示为黄色

2. 将所有数据包记录到日志文件
   - 日志文件位于 `logs/packets/` 目录
   - 文件名格式为 `packets_YYYYMMDD-HHMMSS.log`

### 数据包日志格式

每个数据包日志条目包含以下信息：

```
[方向] [客户端ID]
{
  数据包内容（格式化的JSON）
}
==================================================
```

其中：
- 方向：`RECV`（接收）或 `SEND`（发送）
- 客户端ID：WebSocket 客户端的唯一标识符

## 日志系统

服务器使用分层日志系统，将不同类型的日志存储在不同的文件中。

### 日志文件位置

- 主服务器日志：`logs/server_YYYYMMDD-HHMMSS.log`
- WebSocket 数据包日志：`logs/packets/packets_YYYYMMDD-HHMMSS.log`

### 日志级别

日志系统支持以下级别（从低到高）：

- DEBUG：详细的调试信息
- INFO：一般信息性消息
- WARNING：警告信息
- ERROR：错误信息
- CRITICAL：严重错误信息

可以在配置文件中设置日志级别：

```json
{
  "logging": {
    "level": "INFO"
  }
}
```

### 控制台输出

控制台输出使用彩色编码以提高可读性：

- DEBUG：青色
- INFO：绿色
- WARNING：黄色
- ERROR：红色
- CRITICAL：白色文字，红色背景

## 健康监控

服务器包含内置的连接健康监控系统，可以：

1. 跟踪客户端连接的活动状态
2. 自动关闭不活跃的连接
3. 尝试重新连接断开的客户端

可以在配置文件中调整健康监控参数：

```json
{
  "server": {
    "health_check_interval": 60,
    "connection_timeout": 300,
    "reconnect_attempts": 5,
    "reconnect_delay": 5
  }
}
```

## 常见问题排查

1. **问题**：没有看到数据包日志
   **解决方案**：确保使用 `--debug` 参数启动服务器

2. **问题**：日志文件没有创建
   **解决方案**：检查应用程序是否有写入权限，确保 `logs` 目录可写

3. **问题**：控制台没有彩色输出
   **解决方案**：在 Windows 系统上，彩色输出默认禁用；在配置文件中设置 `"colored_console": true` 可尝试启用 