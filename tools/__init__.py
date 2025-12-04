"""动态生成的工具模块"""

import os
import importlib.util
from pathlib import Path

TOOLS_DIR = Path(__file__).parent


def load_tool(name: str):
    """动态加载工具"""
    tool_path = TOOLS_DIR / f"{name}.py"
    if not tool_path.exists():
        return None
    
    spec = importlib.util.spec_from_file_location(name, tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 返回主函数
    if hasattr(module, name):
        return getattr(module, name)
    return None


def list_tools() -> list:
    """列出所有工具文件"""
    tools = []
    for f in TOOLS_DIR.glob("*.py"):
        if f.name != "__init__.py":
            tools.append(f.stem)
    return tools
