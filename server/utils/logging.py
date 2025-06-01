import logging
import os
import json
from pathlib import Path

def setup_logging(config=None):
    """
    Setup logging configuration based on provided config or default values.
    
    Args:
        config (dict, optional): Logging configuration dictionary. Defaults to None.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if config is None:
        # Default logging configuration
        config = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": None
        }
    
    # Create logger
    logger = logging.getLogger("mc-mcp-server")
    
    # Set level
    level = getattr(logging, config.get("level", "INFO"))
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(config.get("format"))
    
    # Add stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Add file handler if specified
    log_file = config.get("file")
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def load_config(config_file='config/default.json'):
    """
    Load configuration from the specified JSON file.
    
    Args:
        config_file (str, optional): Path to the configuration file. Defaults to 'config/default.json'.
    
    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # Use basic logging to report error
        logging.basicConfig(level=logging.INFO)
        logging.error(f"Error loading config: {e}")
        return {} 