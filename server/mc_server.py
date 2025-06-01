import asyncio
import json
import uuid
import websockets
import logging
from .utils.logging import setup_logging

# Logger instance
logger = logging.getLogger("mc-mcp-server")

class MinecraftServer:
    """
    WebSocket server for Minecraft communication.
    Handles connections with Minecraft clients and processes messages.
    """
    
    def __init__(self, config, message_handler=None):
        """
        Initialize the Minecraft WebSocket server.
        
        Args:
            config (dict): Server configuration
            message_handler (callable, optional): Function to handle incoming messages.
                Should accept client_id, message_type, and message as arguments.
        """
        self.config = config
        
        # 设置主机和端口
        server_config = config.get("server", {})
        
        # 为测试目的，将host设置为localhost
        # 注意：在生产环境中，可以使用config中的值，通常是"0.0.0.0"
        #self.host = server_config.get("host", "0.0.0.0")
        self.host = "localhost"  # 强制使用localhost以便本地测试
        
        self.port = server_config.get("port", 8080)
        
        # 设置WebSocket配置
        self.websocket_config = {
            'ping_interval': server_config.get("ping_interval", 30),
            'ping_timeout': server_config.get("ping_timeout", 15),
            'close_timeout': server_config.get("close_timeout", 15),
            'max_size': server_config.get("max_size", 10 * 1024 * 1024),
            'max_queue': server_config.get("max_queue", 32),
        }
        
        logger.info(f"WebSocket服务器初始化 - 主机: {self.host}, 端口: {self.port}")
        logger.info(f"WebSocket配置: {self.websocket_config}")
        
        self.message_handler = message_handler
        self.server = None
        self.active_connections = {}
    
    async def start(self):
        """
        Start the WebSocket server.
        """
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                **self.websocket_config
            )
            logger.info(f"WebSocket服务器启动成功 - 监听地址: {self.host}:{self.port}")
            logger.info(f"客户端可以使用 ws://{self.host}:{self.port} 进行连接")
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """
        Stop the WebSocket server.
        """
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket服务器已停止")
    
    async def handle_connection(self, websocket, path):
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            path: Connection path
        """
        client_id = str(uuid.uuid4())
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"新客户端连接: {client_info} (ID: {client_id})")
        
        self.active_connections[client_id] = websocket
        
        try:
            # Send welcome message
            welcome_message = self._create_welcome_message(client_id)
            await self.send_message(client_id, welcome_message)
            
            # Subscribe to PlayerMessage event
            await self.subscribe_event(client_id, "PlayerMessage")
            
            # Process messages
            await self.process_messages(client_id, websocket)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"客户端 {client_id} 连接关闭: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 连接时出错: {e}", exc_info=True)
        finally:
            # Remove client from active connections
            if client_id in self.active_connections:
                del self.active_connections[client_id]
            logger.info(f"客户端 {client_id} 已断开连接")
    
    async def process_messages(self, client_id, websocket):
        """
        Process incoming messages from a client.
        
        Args:
            client_id (str): Client identifier
            websocket: WebSocket connection object
        """
        async for message in websocket:
            try:
                # Parse JSON message
                data = json.loads(message)
                logger.debug(f"收到来自客户端 {client_id} 的消息: {message[:200]}...")
                
                # Handle message based on type
                await self.handle_message(client_id, data)
            except json.JSONDecodeError:
                logger.error(f"客户端 {client_id} 发送的JSON无效: {message[:200]}...")
            except Exception as e:
                logger.error(f"处理客户端 {client_id} 消息时出错: {e}", exc_info=True)
    
    async def handle_message(self, client_id, data):
        """
        Handle a parsed message from a client.
        
        Args:
            client_id (str): Client identifier
            data (dict): Parsed message data
        """
        # Check if it's a player message event
        if "header" in data and data["header"].get("eventName") == "PlayerMessage":
            if self.message_handler:
                await self.message_handler(client_id, "PlayerMessage", data)
            else:
                # Default handling for player messages
                sender = data.get("body", {}).get("sender", "")
                message = data.get("body", {}).get("message", "")
                logger.info(f"收到玩家 {sender} 的消息: {message}")
        
        # Check if it's a command response
        elif "header" in data and "requestId" in data["header"]:
            logger.debug(f"命令响应: {data}")
        
        # Unknown message type
        else:
            logger.debug(f"未知消息类型: {data}")
    
    async def send_message(self, client_id, message):
        """
        Send a message to a client.
        
        Args:
            client_id (str): Client identifier
            message (dict): Message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        websocket = self.active_connections.get(client_id)
        if not websocket:
            logger.warning(f"无法向客户端 {client_id} 发送消息: 未连接")
            return False
        
        try:
            message_json = json.dumps(message)
            await websocket.send(message_json)
            logger.debug(f"向客户端 {client_id} 发送消息: {message_json[:200]}...")
            return True
        except Exception as e:
            logger.error(f"向客户端 {client_id} 发送消息时出错: {e}")
            return False
    
    async def broadcast_message(self, message):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message (dict): Message to broadcast
            
        Returns:
            int: Number of clients that received the message
        """
        sent_count = 0
        for client_id in list(self.active_connections.keys()):
            if await self.send_message(client_id, message):
                sent_count += 1
        return sent_count
    
    async def subscribe_event(self, client_id, event_name):
        """
        Subscribe to a Minecraft event.
        
        Args:
            client_id (str): Client identifier
            event_name (str): Name of the event to subscribe to
            
        Returns:
            bool: True if subscription was successful, False otherwise
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
        
        return await self.send_message(client_id, subscription_message)
    
    async def run_command(self, client_id, command):
        """
        Run a Minecraft command.
        
        Args:
            client_id (str): Client identifier
            command (str): Command to run
            
        Returns:
            bool: True if command was sent successfully, False otherwise
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
        
        return await self.send_message(client_id, command_message)
    
    async def send_game_message(self, client_id, message):
        """
        Send a chat message to the game.
        
        Args:
            client_id (str): Client identifier
            message (str): Message content
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        # Escape special characters
        escaped_message = message.replace('"', '\\"').replace(':', '：').replace('%', '\\%')
        
        command = f'tellraw @a {{"rawtext":[{{"text":"§a{escaped_message}"}}]}}'
        return await self.run_command(client_id, command)
    
    async def send_script_event(self, client_id, event_id, content):
        """
        Send a script event to the game.
        
        Args:
            client_id (str): Client identifier
            event_id (str): Script event identifier
            content (str): Event content
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        command = f"scriptevent {event_id} {content}"
        return await self.run_command(client_id, command)
    
    def _create_welcome_message(self, client_id):
        """
        Create a welcome message for a new client.
        
        Args:
            client_id (str): Client identifier
            
        Returns:
            dict: Welcome message
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
    Run the Minecraft WebSocket server.
    
    Args:
        config (dict): Server configuration
    """
    server = MinecraftServer(config)
    await server.start()


if __name__ == "__main__":
    # This code will only run if the file is executed directly
    from .utils.logging import load_config
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    logger = setup_logging(config.get("logging"))
    
    # Run server
    asyncio.run(run_server(config)) 