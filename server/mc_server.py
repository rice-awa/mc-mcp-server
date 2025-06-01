import asyncio
import json
import uuid
import websockets
import logging
import time
import os
from .utils.logging import setup_logging

# Logger instance
logger = logging.getLogger("mc-mcp-server")

class MinecraftServer:
    """
    Minecraft通信的WebSocket服务器。
    处理与Minecraft客户端的连接并处理消息。
    """
    
    def __init__(self, config, event_handler=None, debug_mode=False):
        """
        初始化Minecraft WebSocket服务器。
        
        Args:
            config (dict): 服务器配置
            event_handler (callable, optional): 处理传入事件的函数。
                应接受client_id，event_type和message作为参数。
            debug_mode (bool, optional): 是否启用调试模式
        """
        self.config = config
        self.debug_mode = debug_mode
        
        # 设置主机和端口
        server_config = config.get("server", {})
        
        # 为测试目的，将host设置为localhost
        # 注意：在生产环境中，可以使用config中的值，通常是"0.0.0.0"
        self.host = server_config.get("host", "0.0.0.0")
        
        self.port = server_config.get("port", 8080)
        
        # 设置WebSocket配置
        self.websocket_config = {
            'ping_interval': server_config.get("ping_interval", 30),
            'ping_timeout': server_config.get("ping_timeout", 15),
            'close_timeout': server_config.get("close_timeout", 15),
            'max_size': server_config.get("max_size", 10 * 1024 * 1024),
            'max_queue': server_config.get("max_queue", 32),
        }
        
        # 连接健康状态监控
        self.health_check_interval = server_config.get("health_check_interval", 60)  # 秒
        self.connection_timeout = server_config.get("connection_timeout", 300)  # 秒
        self.reconnect_attempts = server_config.get("reconnect_attempts", 5)
        self.reconnect_delay = server_config.get("reconnect_delay", 5)  # 秒
        
        # 设置日志文件
        self._setup_packet_logging()
        
        logger.info(f"WebSocket服务器初始化 - 主机: {self.host}, 端口: {self.port}")
        logger.info(f"WebSocket配置: {self.websocket_config}")
        logger.info(f"调试模式: {'启用' if self.debug_mode else '禁用'}")
        
        self.event_handler = event_handler
        self.server = None
        self.active_connections = {}
        self.connection_last_activity = {}  # 跟踪每个连接的最后活动时间
        self.health_check_task = None
        self.running = False
    
    def _setup_packet_logging(self):
        """设置数据包日志记录"""
        # 确保日志目录存在
        log_dir = "logs/packets"
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建数据包日志记录器
        self.packet_logger = logging.getLogger("mc-packet-logger")
        self.packet_logger.setLevel(logging.DEBUG)
        
        # 创建文件处理程序
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        packet_log_file = os.path.join(log_dir, f"packets_{timestamp}.log")
        file_handler = logging.FileHandler(packet_log_file, encoding='utf-8')
        
        # 设置格式化程序
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加处理程序到记录器
        self.packet_logger.addHandler(file_handler)
        
        if self.debug_mode:
            logger.info(f"数据包日志将保存到: {packet_log_file}")
    
    def _log_packet(self, direction, client_id, data):
        """
        记录WebSocket数据包
        
        Args:
            direction (str): 数据包方向 ('RECV' 或 'SEND')
            client_id (str): 客户端ID
            data: 数据包内容
        """
        if not self.debug_mode:
            return
        
        try:
            # 将数据格式化为JSON字符串以便于阅读
            if isinstance(data, str):
                try:
                    # 尝试解析JSON字符串
                    parsed_data = json.loads(data)
                    formatted_data = json.dumps(parsed_data, indent=2, ensure_ascii=False)
                except:
                    formatted_data = data
            else:
                formatted_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            # 记录数据包
            log_message = f"[{direction}] [Client: {client_id}]\n{formatted_data}\n{'=' * 50}"
            self.packet_logger.debug(log_message)
            
            # 如果是调试模式，也输出到控制台
            print(f"\033[{'36' if direction == 'RECV' else '33'}m{log_message}\033[0m")
        except Exception as e:
            logger.error(f"记录数据包时出错: {e}")
    
    async def start(self):
        """
        启动WebSocket服务器。
        """
        self.running = True
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                **self.websocket_config
            )
            logger.info(f"WebSocket服务器启动成功 - 监听地址: {self.host}:{self.port}")
            logger.info(f"客户端可以使用 ws://{self.host}:{self.port} 进行连接")
            
            # 启动健康检查任务
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}", exc_info=True)
            raise
        finally:
            self.running = False
    
    async def stop(self):
        """
        停止WebSocket服务器。
        """
        self.running = False
        
        # 取消健康检查任务
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有活动连接
        close_tasks = []
        for client_id, websocket in list(self.active_connections.items()):
            try:
                close_tasks.append(websocket.close(1001, "服务器关闭"))
            except:
                pass
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # 停止服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket服务器已停止")
    
    async def _health_check_loop(self):
        """
        定期检查连接健康状态的循环。
        """
        try:
            while self.running:
                await asyncio.sleep(self.health_check_interval)
                await self._check_connections_health()
        except asyncio.CancelledError:
            logger.debug("健康检查任务已取消")
        except Exception as e:
            logger.error(f"健康检查任务出错: {e}", exc_info=True)
    
    async def _check_connections_health(self):
        """
        检查所有连接的健康状态，关闭不活跃的连接。
        """
        current_time = time.time()
        for client_id in list(self.active_connections.keys()):
            last_activity = self.connection_last_activity.get(client_id, 0)
            if current_time - last_activity > self.connection_timeout:
                logger.warning(f"客户端 {client_id} 连接超时，正在关闭")
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.close(1000, "连接超时")
                except Exception as e:
                    logger.error(f"关闭超时连接时出错: {e}")
                finally:
                    if client_id in self.active_connections:
                        del self.active_connections[client_id]
                    if client_id in self.connection_last_activity:
                        del self.connection_last_activity[client_id]
    
    def _update_activity(self, client_id):
        """
        更新客户端的最后活动时间。
        
        Args:
            client_id (str): 客户端标识符
        """
        self.connection_last_activity[client_id] = time.time()
    
    async def handle_connection(self, websocket):
        """
        处理新的WebSocket连接。
        
        Args:
            websocket: WebSocket连接对象
        """
        client_id = str(uuid.uuid4())
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"新客户端连接: {client_info} (ID: {client_id})")
        
        self.active_connections[client_id] = websocket
        self._update_activity(client_id)
        
        try:
            # 发送欢迎消息
            welcome_message = self._create_welcome_message(client_id)
            
            # 发送欢迎消息文本内容
            await self.send_game_message(client_id, welcome_message["content"])
            
            # 订阅PlayerMessage事件
            await self.subscribe_event(client_id, "PlayerMessage")
            
            # 处理消息
            await self.process_messages(client_id, websocket)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"客户端 {client_id} 连接关闭: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 连接时出错: {e}", exc_info=True)
        finally:
            # 从活动连接中移除客户端
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.connection_last_activity:
                del self.connection_last_activity[client_id]
            logger.info(f"客户端 {client_id} 已断开连接")
    
    async def process_messages(self, client_id, websocket):
        """
        处理来自客户端的传入消息。
        
        Args:
            client_id (str): 客户端标识符
            websocket: WebSocket连接对象
        """
        async for message in websocket:
            try:
                # 更新活动时间
                self._update_activity(client_id)
                
                # 记录接收到的数据包
                self._log_packet("RECV", client_id, message)
                
                # 解析JSON消息
                data = json.loads(message)
                logger.debug(f"收到来自客户端 {client_id} 的消息: {message[:200]}...")
                
                # 根据类型处理消息
                await self.handle_message(client_id, data)
            except json.JSONDecodeError:
                logger.error(f"客户端 {client_id} 发送的JSON无效: {message[:200]}...")
            except Exception as e:
                logger.error(f"处理客户端 {client_id} 消息时出错: {e}", exc_info=True)
    
    async def handle_message(self, client_id, data):
        """
        处理来自客户端的已解析消息。
        
        Args:
            client_id (str): 客户端标识符
            data (dict): 已解析的消息数据
        """
        # 检查是否为玩家消息事件
        if "header" in data and data["header"].get("eventName") == "PlayerMessage":
            if self.event_handler:
                try:
                    await self.event_handler(client_id, "PlayerMessage", data)
                except Exception as e:
                    logger.error(f"事件处理程序出错: {e}", exc_info=True)
            else:
                # 玩家消息的默认处理
                sender = data.get("body", {}).get("sender", "")
                message = data.get("body", {}).get("message", "")
                logger.info(f"收到玩家 {sender} 的消息: {message}")
        
        # 检查是否为命令响应
        elif "header" in data and "requestId" in data["header"]:
            logger.debug(f"命令响应: {data}")
        
        # 未知消息类型
        else:
            logger.debug(f"未知消息类型: {data}")
    
    async def send_data(self, client_id, data):
        """
        向客户端发送数据。
        
        Args:
            client_id (str): 客户端标识符
            data (dict): 要发送的数据
            
        Returns:
            bool: 如果数据成功发送则为True，否则为False
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            logger.warning(f"无法向客户端 {client_id} 发送数据: 未连接")
            return False
        
        try:
            data_json = json.dumps(data)
            
            # 记录发送的数据包
            self._log_packet("SEND", client_id, data)
            
            await websocket.send(data_json)
            # 更新活动时间
            self._update_activity(client_id)
            logger.debug(f"向客户端 {client_id} 发送数据: {data_json[:200]}...")
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"向客户端 {client_id} 发送数据失败: 连接已关闭")
            # 从活动连接中移除客户端
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            if client_id in self.connection_last_activity:
                del self.connection_last_activity[client_id]
            return False
        except Exception as e:
            logger.error(f"向客户端 {client_id} 发送数据时出错: {e}")
            return False
    
    async def broadcast_message(self, message):
        """
        向所有已连接的客户端广播消息。
        
        Args:
            message (dict): 要广播的消息
            
        Returns:
            int: 接收到消息的客户端数量
        """
        sent_count = 0
        for client_id in list(self.active_connections.keys()):
            if await self.send_data(client_id, message):
                sent_count += 1
        return sent_count
    
    async def subscribe_event(self, client_id, event_name):
        """
        订阅Minecraft事件。
        
        Args:
            client_id (str): 客户端标识符
            event_name (str): 要订阅的事件名称
            
        Returns:
            bool: 如果订阅成功则为True，否则为False
        """
        subscription_message = {
            "body": {
                "eventName": event_name
            },
            "header": {
                "requestId": str(uuid.uuid4()),
                "messagePurpose": "subscribe",
                "version": 1,
                "EventName": "commandRequest"
            }
        }
        
        return await self.send_data(client_id, subscription_message)
    
    async def run_command(self, client_id, command, retry_count=0):
        """
        运行Minecraft命令。
        
        Args:
            client_id (str): 客户端标识符
            command (str): 要运行的命令
            retry_count (int, optional): 当前重试次数
            
        Returns:
            bool: 如果命令成功发送则为True，否则为False
        """
        command_message = {
            "body": {
                "origin": {
                    "type": "player"
                },
                "commandLine": command,
                "version": 17039360
            },
            "header": {
                "requestId": str(uuid.uuid4()),
                "messagePurpose": "commandRequest",
                "version": 1,
                "EventName": "commandRequest"
            }
        }
        
        success = await self.send_data(client_id, command_message)
        
        # 如果发送失败且未超过重试次数，尝试重新连接并重试
        if not success and retry_count < self.reconnect_attempts:
            logger.warning(f"命令发送失败，尝试重新连接并重试 (尝试 {retry_count + 1}/{self.reconnect_attempts})")
            reconnected = await self.try_reconnect(client_id)
            if reconnected:
                # 重新连接成功，重试命令
                return await self.run_command(client_id, command, retry_count + 1)
        
        return success
    
    async def run_commands(self, client_id, commands):
        """
        批量运行多个Minecraft命令。
        
        Args:
            client_id (str): 客户端标识符
            commands (list): 要运行的命令列表
            
        Returns:
            bool: 如果所有命令成功发送则为True，否则为False
        """
        all_success = True
        for command in commands:
            success = await self.run_command(client_id, command)
            if not success:
                all_success = False
                logger.warning(f"命令执行失败: {command}")
        return all_success
    
    async def try_reconnect(self, client_id):
        """
        尝试重新连接断开的客户端。
        
        Args:
            client_id (str): 客户端标识符
            
        Returns:
            bool: 如果重新连接成功则为True，否则为False
        """
        # 检查客户端是否已经连接
        if client_id in self.active_connections:
            # 客户端已经连接，无需重新连接
            return True
        
        logger.info(f"尝试重新连接客户端 {client_id}")
        
        # 在实际情况下，WebSocket客户端需要自己重新连接
        # 这里我们只是等待一段时间，看是否有新的连接
        
        for _ in range(self.reconnect_attempts):
            await asyncio.sleep(self.reconnect_delay)
            if client_id in self.active_connections:
                logger.info(f"客户端 {client_id} 已重新连接")
                return True
        
        logger.warning(f"客户端 {client_id} 重新连接失败")
        return False
    
    async def send_game_message(self, client_id, message):
        """
        向游戏内发送聊天消息。
        
        Args:
            client_id (str): 客户端标识符
            message (str): 消息内容
            
        Returns:
            bool: 如果消息成功发送则为True，否则为False
        """
        # 转义特殊字符
        escaped_message = message.replace('"', '\\"').replace(':', '：').replace('%', '\\%')
        
        command = f'tellraw @a {{"rawtext":[{{"text":"§a{escaped_message}"}}]}}'
        return await self.run_command(client_id, command)
    
    async def send_script_event(self, client_id, event_id, content):
        """
        向游戏发送脚本事件。
        
        Args:
            client_id (str): 客户端标识符
            event_id (str): 脚本事件标识符
            content (str): 事件内容
            
        Returns:
            bool: 如果事件成功发送则为True，否则为False
        """
        command = f"scriptevent {event_id} {content}"
        return await self.run_command(client_id, command)
    
    def _create_welcome_message(self, client_id):
        """
        为新客户端创建欢迎消息。
        
        Args:
            client_id (str): 客户端标识符
            
        Returns:
            dict: 欢迎消息
        """
        welcome_text = f"""
-----------
成功连接WebSocket服务器
服务器ip:{self.host}
端口:{self.port}
连接UUID:{client_id}
-----------
        """.strip()
        
        return {
            "type": "welcome",
            "content": welcome_text,
            "client_id": client_id
        }


# Simple usage example
async def run_server(config):
    """
    运行Minecraft WebSocket服务器。
    
    Args:
        config (dict): 服务器配置
    """
    server = MinecraftServer(config)
    await server.start()


if __name__ == "__main__":
    # 仅当文件直接执行时才运行此代码
    from .utils.logging import load_config
    
    # 加载配置
    config = load_config()
    
    # 设置日志
    logger = setup_logging(config.get("logging"))
    
    # 运行服务器
    asyncio.run(run_server(config)) 