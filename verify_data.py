"""数据验证脚本 - 验证MongoDB和Redis中的工具数据"""

import redis
import json
from pymongo import MongoClient

def verify_data():
    print("=== 数据验证 ===")
    print()

    # MongoDB 验证
    print("[MongoDB 验证]")
    try:
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        db = client["selftool"]
        collection = db["tools"]
        
        # 查询 get_current_time 工具
        tool = collection.find_one({"name": "get_current_time"})
        if tool:
            print("  找到工具: get_current_time")
            print(f'    版本: {tool.get("version", "N/A")}')
            print(f'    分类: {tool.get("category", "N/A")}')
            print(f'    描述: {tool.get("description", "N/A")}')
            code = tool.get("code", "")
            if len(code) > 100:
                code = code[:100] + "..."
            print(f"    代码: {code}")
        else:
            print("  未找到工具: get_current_time")
        
        # 列出所有工具
        all_tools = list(collection.find({}, {"name": 1, "category": 1}))
        print(f"  总工具数: {len(all_tools)}")
        for t in all_tools:
            print(f'    - {t["name"]} ({t.get("category", "N/A")})')
    except Exception as e:
        print(f"  连接失败: {e}")

    print()

    # Redis 验证
    print("[Redis 验证]")
    try:
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.ping()
        
        # 检查缓存的工具
        tool_data = r.get("tool:get_current_time")
        if tool_data:
            tool = json.loads(tool_data)
            print("  找到缓存: tool:get_current_time")
            print(f"    TTL: {r.ttl('tool:get_current_time')} 秒")
            print(f'    版本: {tool.get("version", "N/A")}')
        else:
            print("  未找到缓存: tool:get_current_time")
        
        # 列出所有工具缓存
        keys = r.keys("tool:*")
        print(f"  缓存键数: {len(keys)}")
        for k in keys:
            print(f"    - {k}")
    except Exception as e:
        print(f"  连接失败: {e}")

    print()
    print("=== 验证完成 ===")


if __name__ == "__main__":
    verify_data()
