"""安全沙箱执行模块"""

import ast
import builtins
from typing import Any


class SafeExecutor:
    """安全沙箱执行器"""
    
    # 允许的安全模块名称
    ALLOWED_MODULE_NAMES = {
        "datetime", "time", "calendar", "math", 
        "json", "re", "random", "string"
    }
    
    def _safe_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """安全导入函数，只允许白名单模块"""
        module_name = name.split('.')[0]
        if module_name not in self.ALLOWED_MODULE_NAMES:
            raise ImportError(f"禁止导入模块: {name}")
        return __import__(name, globals, locals, fromlist, level)
    
    def _get_safe_builtins(self) -> dict:
        """获取安全的内置函数"""
        return {
            # 常量
            "True": True, 
            "False": False, 
            "None": None,
            # 类型
            "str": str, 
            "int": int, 
            "float": float, 
            "bool": bool,
            "list": list, 
            "dict": dict, 
            "tuple": tuple, 
            "set": set,
            "frozenset": frozenset, 
            "bytes": bytes,
            # 函数
            "len": len, 
            "range": range, 
            "enumerate": enumerate,
            "zip": zip, 
            "map": map, 
            "filter": filter,
            "min": min, 
            "max": max, 
            "sum": sum, 
            "abs": abs,
            "round": round, 
            "sorted": sorted, 
            "reversed": reversed,
            "all": all, 
            "any": any, 
            "isinstance": isinstance,
            "type": type, 
            "repr": repr, 
            "format": format,
            "print": lambda *args, **kwargs: None,
            # 安全导入
            "__import__": self._safe_import,
        }
    
    def execute(self, code: str, func_name: str) -> Any:
        """安全执行代码并返回结果"""
        safe_globals = {
            "__builtins__": self._get_safe_builtins(),
        }
        
        exec(code, safe_globals)
        
        if func_name not in safe_globals:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    break
        
        func = safe_globals.get(func_name)
        if not callable(func):
            raise ValueError(f"函数 {func_name} 未找到或不可调用")
        
        return func()
