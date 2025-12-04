"""代码安全检查模块"""

import ast
from typing import List


class CodeSafetyChecker:
    """代码安全检查器"""
    
    # 禁止的导入模块
    FORBIDDEN_IMPORTS = {
        "os", "subprocess", "sys", "shutil",
        "socket", "requests", "urllib", "http",
        "pickle", "shelve", "sqlite3",
        "ctypes", "multiprocessing", "threading",
        "asyncio", "concurrent",
    }
    
    # 禁止的内置函数
    FORBIDDEN_BUILTINS = {
        "eval", "exec", "compile",
        "__import__", "open", "input",
        "globals", "locals", "vars",
        "getattr", "setattr", "delattr",
        "breakpoint", "exit", "quit",
    }
    
    def check_all(self, code: str) -> List[str]:
        """执行所有安全检查"""
        issues = []
        issues.extend(self._check_imports(code))
        issues.extend(self._check_builtins(code))
        issues.extend(self._check_ast(code))
        return issues
    
    def _check_imports(self, code: str) -> List[str]:
        """检查禁止的导入"""
        issues = []
        for mod in self.FORBIDDEN_IMPORTS:
            if f"import {mod}" in code or f"from {mod}" in code:
                issues.append(f"禁止导入模块: {mod}")
        return issues
    
    def _check_builtins(self, code: str) -> List[str]:
        """检查禁止的内置函数"""
        issues = []
        for func in self.FORBIDDEN_BUILTINS:
            if f"{func}(" in code:
                issues.append(f"禁止使用函数: {func}")
        return issues
    
    def _check_ast(self, code: str) -> List[str]:
        """AST 深度检查"""
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod_name = alias.name.split('.')[0]
                        if mod_name in self.FORBIDDEN_IMPORTS:
                            issues.append(f"AST检测到禁止导入: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod_name = node.module.split('.')[0]
                        if mod_name in self.FORBIDDEN_IMPORTS:
                            issues.append(f"AST检测到禁止导入: {node.module}")
                
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.FORBIDDEN_BUILTINS:
                            issues.append(f"AST检测到禁止调用: {node.func.id}")
                            
        except SyntaxError as e:
            issues.append(f"代码语法错误: {e}")
        
        return issues
