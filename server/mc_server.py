import asyncio
import json
import uuid
import websockets
import logging
from .utils.logging import setup_logging

# Dictionary to store active connections
# Format: {client_id: websocket}
active_connections = {}

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
        self.host = config.get("server", {}).get("host", "0.0.0.0")
        self.port = config.get("server", {}).get("port", 8080)
        self.websocket_config = {
            'ping_interval': config.get("server", {}).get("ping_interval", 30),
            'ping_timeout': config.get("server", {}).get("ping_timeout", 15),
            'close_timeout': config.get("server", {}).get("close_timeout", 15),
            'max_size': config.get("server", {}).get("max_size", 10 * 1024 * 1024),
            'max_queue': config.get("server", {}).get("max_queue", 32),
            'read_limit': config.get("server", {}).get("read_limit", 65536),
            'write_limit': config.get("server", {}).get("write_limit", 65536),
        }
        self.message_handler = message_handler
        self.server = None
    
    async def start(self):
        """
        Start the WebSocket server.
        """
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            **self.websocket_config
        )
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
        await self.server.wait_closed()
    
    async def stop(self):
        """
        Stop the WebSocket server.
        """
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
    
    async def handle_connection(self, websocket, path):
        """
        Handle a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            path: Connection path
        """
        client_id = str(uuid.uuid4())
        active_connections[client_id] = websocket
        
        try:
            # Send welcome message
            welcome_message = self._create_welcome_message(client_id)
            await self.send_message(client_id, welcome_message)
            
            # Subscribe to PlayerMessage event
            await self.subscribe_event(client_id, "PlayerMessage")
            
            # Process messages
            await self.process_messages(client_id, websocket)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed for client {client_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling connection for client {client_id}: {e}", exc_info=True)
        finally:
            # Remove client from active connections
            if client_id in active_connections:
                del active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
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
                
                # Handle message based on type
                await self.handle_message(client_id, data)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {client_id}: {message}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}", exc_info=True)
    
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
                logger.info(f"Player message from {sender}: {message}")
        
        # Check if it's a command response
        elif "header" in data and "requestId" in data["header"]:
            logger.debug(f"Command response: {data}")
        
        # Unknown message type
        else:
            logger.debug(f"Unknown message type: {data}")
    
    async def send_message(self, client_id, message):
        """
        Send a message to a client.
        
        Args:
            client_id (str): Client identifier
            message (dict): Message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        websocket = active_connections.get(client_id)
        if not websocket:
            logger.warning(f"Cannot send message to client {client_id}: not connected")
            return False
        
        try:
            await websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
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
        for client_id in list(active_connections.keys()):
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