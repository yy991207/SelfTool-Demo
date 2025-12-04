"""测试用例"""

import pytest
import asyncio
from src.state import create_initial_state
from src.safety import CodeSafetyChecker
from src.sandbox import SafeExecutor


class TestSafety:
    """安全检查测试"""
    
    def test_forbidden_import(self):
        """测试禁止的导入"""
        checker = CodeSafetyChecker()
        code = "import os\nos.system('ls')"
        issues = checker.check_all(code)
        assert len(issues) > 0
        assert any("os" in issue for issue in issues)
    
    def test_safe_code(self):
        """测试安全代码"""
        checker = CodeSafetyChecker()
        code = """
def get_time() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')
"""
        issues = checker.check_all(code)
        assert len(issues) == 0


class TestSandbox:
    """沙箱执行测试"""
    
    def test_execute_safe_code(self):
        """测试执行安全代码"""
        executor = SafeExecutor()
        code = """
def get_greeting() -> str:
    return "Hello, World!"
"""
        result = executor.execute(code, "get_greeting")
        assert result == "Hello, World!"
    
    def test_execute_datetime(self):
        """测试执行时间函数"""
        executor = SafeExecutor()
        code = """
def get_time() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')
"""
        result = executor.execute(code, "get_time")
        assert len(result) == 10  # YYYY-MM-DD


class TestState:
    """状态测试"""
    
    def test_create_initial_state(self):
        """测试创建初始状态"""
        state = create_initial_state("测试请求")
        assert state["user_request"] == "测试请求"
        assert state["generation_attempt"] == 0
        assert state["safety_status"] == "pending"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
