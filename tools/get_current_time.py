"""
工具名称: get_current_time
描述: 获取当前时间
参数: {}
自动生成时间: 2025-12-04 09:09:50
"""

def get_current_time() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 工具元信息
__tool_meta__ = {
    "name": "get_current_time",
    "description": "获取当前时间",
    "parameters": {},
    "category": "datetime"
}


if __name__ == "__main__":
    # 测试执行
    result = get_current_time()
    print(f"执行结果: {result}")
