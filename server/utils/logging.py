import logging
import os
import json
import sys
import time
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """
    自定义格式化程序，为控制台输出添加颜色
    """
    COLORS = {
        'DEBUG': '\033[36m',  # 青色
        'INFO': '\033[32m',   # 绿色
        'WARNING': '\033[33m', # 黄色
        'ERROR': '\033[31m',   # 红色
        'CRITICAL': '\033[41m\033[37m', # 白色文字，红色背景
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_message = super().format(record)
        level_name = record.levelname
        if level_name in self.COLORS:
            return f"{self.COLORS[level_name]}{log_message}{self.RESET}"
        return log_message

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
            "file": None,
            "colored_console": True
        }
    
    # Create logger
    logger = logging.getLogger("mc-agent-server")
    
    # Set level
    level_name = config.get("level", "INFO")
    level = getattr(logging, level_name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    log_format = config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    standard_formatter = logging.Formatter(log_format)
    
    # Add stream handler
    stream_handler = logging.StreamHandler()
    if config.get("colored_console", True) and sys.platform != "win32":
        # 在非Windows平台上使用彩色输出
        stream_handler.setFormatter(ColoredFormatter(log_format))
    else:
        stream_handler.setFormatter(standard_formatter)
    logger.addHandler(stream_handler)
    
    # Add file handler if specified
    log_file = config.get("file")
    if log_file:
        setup_file_handler(logger, log_file, standard_formatter)
    
    # 设置根记录器的级别，这样其他模块的日志也会显示
    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET:
        root_logger.setLevel(level)
    
    return logger

def setup_file_handler(logger, log_file, formatter=None):
    """
    为记录器设置文件处理程序
    
    Args:
        logger (logging.Logger): 要添加处理程序的记录器
        log_file (str): 日志文件路径
        formatter (logging.Formatter, optional): 格式化程序。默认为None。
    """
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Create formatter if not provided
    if formatter is None:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Create and add file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return file_handler

def setup_daily_rotating_file_handler(logger, log_dir, prefix="server", formatter=None):
    """
    设置每日轮换的日志文件处理程序
    
    Args:
        logger (logging.Logger): 要添加处理程序的记录器
        log_dir (str): 日志目录
        prefix (str, optional): 日志文件前缀。默认为"server"。
        formatter (logging.Formatter, optional): 格式化程序。默认为None。
    
    Returns:
        str: 创建的日志文件路径
    """
    # Create directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    log_file = os.path.join(log_dir, f"{prefix}_{timestamp}.log")
    
    # Setup file handler
    setup_file_handler(logger, log_file, formatter)
    
    return log_file

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