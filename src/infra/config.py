"""配置管理模块"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件 (项目根目录/.env)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """全局配置"""
    
    # LLM API 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv(
        "DASHSCOPE_BASE_URL", 
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    LLM_MODEL: str = "qwen-plus"  # 通义千问模型
    
    # MongoDB 配置
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "selftool")
    MONGODB_COLLECTION: str = "tools"
    
    # Redis 配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_TTL: int = 3600  # 缓存过期时间 (秒)
    
    # 工具生成配置
    MAX_GENERATION_ATTEMPTS: int = 3  # 最大重试次数
    EXECUTION_TIMEOUT: int = 5  # 执行超时 (秒)


config = Config()
