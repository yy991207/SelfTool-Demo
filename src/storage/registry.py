"""MongoDB 工具注册模块"""

from typing import Optional, List
from pathlib import Path
from ..infra.config import config
from .cache import tool_cache
from ..infra.connection_manager import connection_manager

# 工具文件存储目录 (项目根目录/tools)
TOOLS_DIR = Path(__file__).parent.parent.parent / "tools"
TOOLS_DIR.mkdir(exist_ok=True)


class ToolRegistry:
    """工具注册管理器 (MongoDB)"""
    
    def _get_collection(self):
        """获取集合（通过连接管理器）"""
        return connection_manager.db.get_collection()
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return connection_manager.db.is_connected()
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        collection = self._get_collection()
        if collection is None:
            return []
        
        try:
            return [doc["name"] for doc in collection.find({}, {"name": 1})]
        except Exception:
            return []
    
    def get_tool(self, name: str) -> Optional[dict]:
        """获取指定工具"""
        cached = tool_cache.get_tool(name)
        if cached:
            return cached
        
        collection = self._get_collection()
        if collection is None:
            return None
        
        try:
            doc = collection.find_one({"name": name})
            if doc:
                doc.pop("_id", None)
                tool_cache.set_tool(doc)
                return doc
        except Exception:
            pass
        return None
    
    def register(self, spec: dict) -> bool:
        """注册工具到数据库"""
        collection = self._get_collection()
        if collection is None:
            return False
        
        try:
            collection.update_one(
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
        collection = self._get_collection()
        if collection is None:
            return tool_cache.search_by_category(category)
        
        try:
            docs = list(collection.find({"category": category}))
            for doc in docs:
                doc.pop("_id", None)
            return docs
        except Exception:
            return []
    
    def get_tools_summary(self, category: str = None) -> str:
        """获取工具摘要文本（供 LLM 判断）"""
        if category:
            tools = self.search_by_category(category)
        else:
            collection = self._get_collection()
            tools = []
            if collection:
                try:
                    docs = list(collection.find({}, {"name": 1, "description": 1, "category": 1}))
                    for doc in docs:
                        doc.pop("_id", None)
                    tools = docs
                except Exception:
                    pass
        
        if not tools:
            return ""
        
        return "\n".join([
            f"- {t['name']}: {t.get('description', '无描述')}"
            for t in tools
        ])


# 全局注册实例
tool_registry = ToolRegistry()
