"""Redis 缓存管理模块"""

import json
from typing import Optional
import redis
from .config import config
from .connection_manager import connection_manager


class ToolCache:
    """工具缓存管理器 (Redis)"""
    
    def _get_client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端（通过连接管理器）"""
        return connection_manager.cache.get_client()
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return connection_manager.cache.is_connected()
    
    def get_tool(self, name: str) -> Optional[dict]:
        """从缓存获取工具"""
        client = self._get_client()
        if not client:
            return None
        
        try:
            data = client.get(f"tool:{name}")
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None
    
    def set_tool(self, spec: dict) -> bool:
        """缓存工具"""
        client = self._get_client()
        if not client:
            return False
        
        try:
            key = f"tool:{spec['name']}"
            client.setex(key, config.REDIS_TTL, json.dumps(spec, ensure_ascii=False))
            return True
        except Exception:
            return False
    
    def search_by_category(self, category: str) -> list:
        """按分类搜索缓存的工具"""
        client = self._get_client()
        if not client:
            return []
        
        try:
            keys = client.keys("tool:*")
            tools = []
            for key in keys:
                data = client.get(key)
                if data:
                    tool = json.loads(data)
                    if tool.get("category") == category:
                        tools.append(tool)
            return tools
        except Exception:
            return []
    
    def clear_all(self) -> bool:
        """清除所有缓存"""
        client = self._get_client()
        if not client:
            return False
        
        try:
            keys = client.keys("tool:*")
            if keys:
                client.delete(*keys)
            return True
        except Exception:
            return False


# 全局缓存实例
tool_cache = ToolCache()
