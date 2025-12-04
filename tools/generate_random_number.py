"""
工具名称: generate_random_number
描述: 生成一个1到100之间的随机数
参数: {}
自动生成时间: 2025-12-04 08:46:09
"""

def generate_random_number() -> str:
    import random
    return str(random.randint(1, 100))


# 工具元信息
__tool_meta__ = {
    "name": "generate_random_number",
    "description": "生成一个1到100之间的随机数",
    "parameters": {},
    "category": "random"
}


if __name__ == "__main__":
    # 测试执行
    result = generate_random_number()
    print(f"执行结果: {result}")
