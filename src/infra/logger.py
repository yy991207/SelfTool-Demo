"""日志模块"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# 创建日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
DETAILED_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
SIMPLE_FORMAT = "%(levelname)-8s | %(message)s"


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """创建并配置 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台 handler (详细)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
    logger.addHandler(console_handler)
    
    # 文件 handler
    log_file = LOG_DIR / f"selftool_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
    logger.addHandler(file_handler)
    
    return logger


# 预定义的 loggers
llm_logger = setup_logger("LLM")
sandbox_logger = setup_logger("SANDBOX")
safety_logger = setup_logger("SAFETY")
registry_logger = setup_logger("REGISTRY")
workflow_logger = setup_logger("WORKFLOW")
