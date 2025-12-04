"""统一连接管理模块

提供数据库连接池和缓存管理器的统一管理入口
"""

from typing import Optional
import redis
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from .config import config


class DatabasePool:
    """MongoDB 数据库连接池"""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._connected = False
    
    def connect(self) -> bool:
        """建立连接"""
        if self._client is not None:
            return self._connected
        
        try:
            self._client = MongoClient(
                config.MONGODB_URI,
                serverSelectionTimeoutMS=2000,
                maxPoolSize=10,
                minPoolSize=1
            )
            self._client.admin.command('ping')
            self._connected = True
        except ConnectionFailure:
            self._connected = False
            self._client = None
        return self._connected
    
    def get_client(self) -> Optional[MongoClient]:
        """获取 MongoDB 客户端"""
        if self._client is None:
            self.connect()
        return self._client
    
    def get_database(self, db_name: str = None):
        """获取数据库实例"""
        client = self.get_client()
        if client is None:
            return None
        return client[db_name or config.MONGODB_DB]
    
    def get_collection(self, collection_name: str = None, db_name: str = None):
        """获取集合实例"""
        db = self.get_database(db_name)
        if db is None:
            return None
        return db[collection_name or config.MONGODB_COLLECTION]
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._client is None:
            self.connect()
        return self._connected
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False


class CacheManager:
    """Redis 缓存管理器"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
        self._connected = False
    
    def connect(self) -> bool:
        """建立连接"""
        if self._client is not None:
            return self._connected
        
        try:
            self._pool = redis.ConnectionPool(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
                max_connections=10
            )
            self._client = redis.Redis(connection_pool=self._pool, socket_timeout=2)
            self._client.ping()
            self._connected = True
        except redis.ConnectionError:
            self._connected = False
            self._client = None
            self._pool = None
        return self._connected
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        if self._client is None:
            self.connect()
        return self._client
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._client is None:
            self.connect()
        return self._connected
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
        if self._pool:
            self._pool.disconnect()
            self._pool = None
        self._connected = False


class ConnectionManager:
    """统一连接管理器（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._db_pool = DatabasePool()
        self._cache_manager = CacheManager()
        self._initialized = True
    
    @property
    def db(self) -> DatabasePool:
        """获取数据库连接池"""
        return self._db_pool
    
    @property
    def cache(self) -> CacheManager:
        """获取缓存管理器"""
        return self._cache_manager
    
    def connect_all(self) -> dict:
        """连接所有服务"""
        return {
            "mongodb": self._db_pool.connect(),
            "redis": self._cache_manager.connect()
        }
    
    def check_status(self) -> dict:
        """检查所有连接状态"""
        return {
            "mongodb": self._db_pool.is_connected(),
            "redis": self._cache_manager.is_connected()
        }
    
    def close_all(self):
        """关闭所有连接"""
        self._db_pool.close()
        self._cache_manager.close()


# 全局连接管理器实例
connection_manager = ConnectionManager()
