import aiohttp
import json
import logging
import os
import re
import time

logger = logging.getLogger("mc-mcp-server")

class LLMConversation:
    """
    Handles conversations with a Language Learning Model (LLM) API.
    Supports streaming responses and context management.
    """
    
    def __init__(self, api_url, api_key, model, system_prompt="", enable_history=True):
        """
        Initialize a new LLM conversation.
        
        Args:
            api_url (str): The URL of the LLM API
            api_key (str): API key for authentication
            model (str): The model to use (e.g., "deepseek-ai/DeepSeek-R1")
            system_prompt (str, optional): System prompt to guide the model's behavior
            enable_history (bool, optional): Whether to maintain conversation history. Defaults to True.
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.enable_history = enable_history
        self.conversation_history = []
        self.session = None
        
    async def __aenter__(self):
        """
        Context manager entry.
        """
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc, tb):
        """
        Context manager exit.
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    def log_message(self, message, role="system"):
        """
        Log a message for debugging purposes.
        
        Args:
            message (str): Message content
            role (str, optional): Message role. Defaults to "system".
        """
        logger.debug(f"[{role}]: {message}")
    
    async def call_gpt(self, prompt):
        """
        Call the LLM API with the given prompt.
        
        Args:
            prompt (str): User prompt
            
        Yields:
            dict: Chunks of the response with format:
                {"reasoning_content": str, "content": str}
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Add user message to history if enabled
        if self.enable_history:
            self.conversation_history.append({"role": "user", "content": prompt})
        
        # Prepare the messages
        messages = []
        
        # Add system prompt if provided
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Add conversation history if enabled
        if self.enable_history:
            messages.extend(self.conversation_history)
        else:
            # Just add the current prompt if history is disabled
            messages.append({"role": "user", "content": prompt})
        
        # Prepare the request data
        request_data = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": None
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        self.log_message(f"Calling LLM API with model: {self.model}")
        
        try:
            async with self.session.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=60
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.log_message(f"API error: {response.status} - {error_text}")
                    yield {"reasoning_content": "", "content": f"Error: API returned status {response.status}"}
                    return
                
                # Process streaming response
                reasoning_buffer = ""
                content_buffer = ""
                
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    
                    # Skip empty lines
                    if not line_text:
                        continue
                        
                    # Skip "data: " prefix
                    if line_text.startswith("data: "):
                        line_text = line_text[6:]
                        
                    # Check for the end of the stream
                    if line_text == "[DONE]":
                        break
                        
                    try:
                        # Parse the JSON data
                        data = json.loads(line_text)
                        
                        # Extract content based on API response format
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        
                        # Get reasoning content (if available)
                        if "tool_calls" in delta:
                            tool_content = delta["tool_calls"][0]["function"]["arguments"]
                            reasoning_match = re.search(r'"reasoning":\s*"(.*?)"', tool_content, re.DOTALL)
                            if reasoning_match:
                                reasoning_content = reasoning_match.group(1)
                                reasoning_buffer += reasoning_content
                        
                        # Get regular content
                        content = delta.get("content", "")
                        if content:
                            content_buffer += content
                        
                        # Yield content when available
                        if reasoning_buffer or content_buffer:
                            yield {
                                "reasoning_content": reasoning_buffer,
                                "content": content_buffer
                            }
                            reasoning_buffer = ""
                            content_buffer = ""
                            
                    except json.JSONDecodeError:
                        self.log_message(f"Failed to parse JSON: {line_text}")
                    except Exception as e:
                        self.log_message(f"Error processing response chunk: {e}")
            
            # Extract the full assistant response to add to history
            if self.enable_history:
                # The last content we've accumulated
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": content_buffer
                })
                
        except aiohttp.ClientError as e:
            self.log_message(f"API request error: {e}")
            yield {"reasoning_content": "", "content": f"Error: API request failed - {e}"}
        except Exception as e:
            self.log_message(f"Unexpected error: {e}")
            yield {"reasoning_content": "", "content": f"Error: Unexpected error - {e}"}
    
    async def clean_history(self):
        """
        Clear the conversation history.
        """
        self.conversation_history = []
        self.log_message("Conversation history cleared")
        
    def set_enable_history(self, enable):
        """
        Enable or disable conversation history.
        
        Args:
            enable (bool): Whether to enable history
        """
        self.enable_history = enable
        self.log_message(f"Conversation history {'enabled' if enable else 'disabled'}")
        
    def get_history(self):
        """
        Get the current conversation history.
        
        Returns:
            list: Conversation history
        """
        return self.conversation_history.copy()


# Factory function to create a new conversation
async def create_conversation(config):
    """
    Create a new LLM conversation instance.
    
    Args:
        config (dict): Configuration dictionary with LLM settings
        
    Returns:
        LLMConversation: Configured conversation instance
    """
    api_url = config.get("llm", {}).get("api_url", os.getenv("API_URL"))
    api_key = os.getenv("API_KEY")
    model = config.get("llm", {}).get("model", "deepseek-chat")
    system_prompt = config.get("llm", {}).get("system_prompt", "")
    enable_history = config.get("llm", {}).get("enable_history", True)
    
    if not api_url:
        raise ValueError("API_URL not set in config or environment variables")
    if not api_key:
        raise ValueError("API_KEY not set in environment variables")
    
    return LLMConversation(
        api_url=api_url,
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        enable_history=enable_history
    ) 