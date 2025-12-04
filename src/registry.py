"""MongoDB 工具注册模块"""

from typing import Optional, List
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from .config import config
from .cache import tool_cache

# 工具文件存储目录
TOOLS_DIR = Path(__file__).parent.parent / "tools"
TOOLS_DIR.mkdir(exist_ok=True)


class ToolRegistry:
    """工具注册管理器 (MongoDB)"""
    
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db = None
        self._collection = None
        self._connected = False
    
    def _connect(self):
        """连接 MongoDB"""
        if self._client is None:
            try:
                self._client = MongoClient(
                    config.MONGODB_URI, 
                    serverSelectionTimeoutMS=2000
                )
                self._client.admin.command('ping')
                self._db = self._client[config.MONGODB_DB]
                self._collection = self._db[config.MONGODB_COLLECTION]
                self._connected = True
            except ConnectionFailure:
                print("[WARN] MongoDB 连接失败，将使用内存存储")
                self._connected = False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        self._connect()
        return self._connected
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        self._connect()
        if not self._connected:
            return []
        
        try:
            return [doc["name"] for doc in self._collection.find({}, {"name": 1})]
        except Exception:
            return []
    
    def get_tool(self, name: str) -> Optional[dict]:
        """获取指定工具"""
        # 先查缓存
        cached = tool_cache.get_tool(name)
        if cached:
            return cached
        
        # 查数据库
        self._connect()
        if not self._connected:
            return None
        
        try:
            doc = self._collection.find_one({"name": name})
            if doc:
                doc.pop("_id", None)
                tool_cache.set_tool(doc)
                return doc
        except Exception:
            pass
        return None
    
    def register(self, spec: dict) -> bool:
        """注册工具到数据库"""
        self._connect()
        if not self._connected:
            return False
        
        try:
            self._collection.update_one(
                {"name": spec["name"]},
                {"$set": spec},
                upsert=True
            )
            tool_cache.set_tool(spec)
            return True
        except Exception:
            return False
    
    def save_as_file(self, spec: dict) -> str:
        """保存工具为 Python 文件"""
        name = spec["name"]
        code = spec["code"]
        description = spec.get("description", "")
        parameters = spec.get("parameters", {})
        
        # 生成文件内容
        file_content = f'''"""
工具名称: {name}
描述: {description}
参数: {parameters}
自动生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

{code}


# 工具元信息
__tool_meta__ = {{
    "name": "{name}",
    "description": "{description}",
    "parameters": {parameters},
    "category": "{spec.get('category', 'other')}"
}}


if __name__ == "__main__":
    # 测试执行
    result = {name}()
    print(f"执行结果: {{result}}")
'''
        
        # 写入文件
        file_path = TOOLS_DIR / f"{name}.py"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        return str(file_path)
    
    def list_tool_files(self) -> List[str]:
        """列出所有工具文件"""
        files = []
        for f in TOOLS_DIR.glob("*.py"):
            if f.name != "__init__.py":
                files.append(f.stem)
        return files
    
    def load_tool_from_file(self, name: str):
        """从文件加载工具"""
        import importlib.util
        
        file_path = TOOLS_DIR / f"{name}.py"
        if not file_path.exists():
            return None
        
        spec = importlib.util.spec_from_file_location(name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, name):
            return getattr(module, name)
        return None
    
    def search_by_category(self, category: str) -> List[dict]:
        """按分类搜索工具"""
        self._connect()
        if not self._connected:
            return tool_cache.search_by_category(category)
        
        try:
            docs = list(self._collection.find({"category": category}))
            for doc in docs:
                doc.pop("_id", None)
            return docs
        except Exception:
            return []
    
    def semantic_search(self, query: str, category: str = None) -> Optional[dict]:
        """语义搜索匹配工具 (简单关键词匹配)"""
        query_lower = query.lower()
        keywords = set(query_lower.split())
        
        # 时间相关关键词
        time_keywords = {"时间", "几点", "time", "clock", "hour", "minute"}
        date_keywords = {"日期", "date", "today", "日历", "calendar", "星期"}
        math_keywords = {"计算", "math", "加", "减", "乘", "除", "求和"}
        
        # 判断类别
        detected_category = None
        if keywords & time_keywords:
            detected_category = "datetime"
        elif keywords & date_keywords:
            detected_category = "calendar"
        elif keywords & math_keywords:
            detected_category = "math"
        
        if detected_category:
            tools = self.search_by_category(detected_category)
            if tools:
                return tools[0]
        
        return None


# 全局注册实例
tool_registry = ToolRegistry()
