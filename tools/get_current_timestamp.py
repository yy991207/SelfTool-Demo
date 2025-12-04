"""
工具名称: get_current_timestamp
描述: 获取当前日期和时间的字符串表示
参数: {}
自动生成时间: 2025-12-04 09:11:13
"""

def get_current_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 工具元信息
__tool_meta__ = {
    "name": "get_current_timestamp",
    "description": "获取当前日期和时间的字符串表示",
    "parameters": {},
    "category": "datetime"
}


if __name__ == "__main__":
    # 测试执行
    result = get_current_timestamp()
    print(f"执行结果: {result}")
