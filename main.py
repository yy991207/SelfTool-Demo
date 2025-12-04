"""SelfTool Demo 入口文件"""

import asyncio
from src.graph import self_tool_graph
from src.state import create_initial_state
from src.cache import tool_cache
from src.registry import tool_registry


def print_banner():
    """打印横幅"""
    print("=" * 50)
    print("  SelfTool Demo - LLM 动态工具生成")
    print("=" * 50)


def check_connections():
    """检查数据库连接"""
    print("\n[检查连接]")
    
    mongo_ok = tool_registry.is_connected()
    redis_ok = tool_cache.is_connected()
    
    print(f"  MongoDB: {'OK' if mongo_ok else 'FAIL (将使用内存存储)'}")
    print(f"  Redis:   {'OK' if redis_ok else 'FAIL (将禁用缓存)'}")
    
    return mongo_ok or redis_ok  # 至少有一个可用


async def run_demo(user_request: str):
    """运行演示"""
    print(f"\n用户请求: {user_request}")
    print("-" * 50)
    
    # 创建初始状态
    state = create_initial_state(user_request)
    
    # 运行图
    result = await self_tool_graph.ainvoke(state)
    
    # 输出结果
    print("\n" + "=" * 50)
    
    if result.get("error"):
        print(f"错误: {result['error']}")
    elif not result.get("need_tool", True):
        # 直接回复，不需要工具
        print(f"回复: {result.get('execution_result', 'N/A')}")
    else:
        # 工具执行结果
        print(f"执行结果: {result.get('execution_result', 'N/A')}")
        if result.get('tool_file'):
            print(f"工具文件: {result.get('tool_file')}")
        print(f"工具已注册: {result.get('tool_registered', False)}")
        print(f"工具已缓存: {result.get('tool_cached', False)}")
        elapsed = result.get('execution_time_ms', 0)
        print(f"执行耗时: {elapsed:.3f}ms" if isinstance(elapsed, float) else f"执行耗时: {elapsed}ms")
    
    print("=" * 50)
    
    return result


async def interactive_mode():
    """交互模式"""
    print_banner()
    check_connections()
    
    print("\n" + "=" * 50)
    print("  交互模式已启动")
    print("  输入你的请求，LLM 将自动生成工具并执行")
    print("  输入 'exit' 或 'quit' 退出")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n>>> 请输入请求: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n再见!")
                break
            
            if user_input.lower() == 'clear':
                # 清除已注册的工具
                from src.registry import tool_registry
                print("清除工具缓存...")
                continue
            
            if user_input.lower() == 'list':
                # 列出已注册工具
                from src.registry import tool_registry, TOOLS_DIR
                tools = tool_registry.list_tools()
                files = tool_registry.list_tool_files()
                print(f"\n数据库中的工具: {tools if tools else '(无)'}")
                print(f"工具文件目录: {TOOLS_DIR}")
                print(f"工具文件列表: {files if files else '(无)'}")
                continue
            
            await run_demo(user_input)
            
        except KeyboardInterrupt:
            print("\n\n中断，再见!")
            break
        except Exception as e:
            print(f"\n错误: {e}")


async def main():
    """主函数"""
    await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
