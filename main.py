"""SelfTool Demo 入口文件"""

import asyncio
import atexit
import uuid
from src.workflow import self_tool_graph, create_initial_state
from src.infra import connection_manager
from src.storage import tool_registry, TOOLS_DIR, checkpointer


# 全局会话 ID
current_thread_id: str = None


def print_banner():
    """打印横幅"""
    print("=" * 50)
    print("  SelfTool Demo - LLM 动态工具生成")
    print("=" * 50)


def init_connections():
    """初始化所有连接"""
    print("\n[初始化连接]")
    status = connection_manager.connect_all()
    
    print(f"  MongoDB: {'OK' if status['mongodb'] else 'FAIL (将使用内存存储)'}")
    print(f"  Redis:   {'OK' if status['redis'] else 'FAIL (将禁用缓存)'}")
    
    return status['mongodb'] or status['redis']


def check_connections():
    """检查连接状态"""
    status = connection_manager.check_status()
    return status['mongodb'] or status['redis']


def close_connections():
    """关闭所有连接"""
    print("\n[关闭连接]")
    connection_manager.close_all()
    print("  所有连接已关闭")


async def run_demo(user_request: str, thread_id: str = None):
    """运行演示"""
    print(f"\n用户请求: {user_request}")
    print(f"会话 ID: {thread_id}")
    print("-" * 50)
    
    # 只传入当前请求，checkpoint 会自动恢复历史状态
    input_state = {"user_request": user_request}
    
    # 运行图（带会话配置）
    config = {"configurable": {"thread_id": thread_id}} if thread_id else None
    result = await self_tool_graph.ainvoke(input_state, config=config)
    
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


def new_session() -> str:
    """创建新会话"""
    global current_thread_id
    current_thread_id = str(uuid.uuid4())[:8]
    return current_thread_id


def show_session_info():
    """显示会话信息"""
    print(f"\n当前会话: {current_thread_id}")
    threads = checkpointer.list_threads()
    print(f"所有会话: {threads if threads else '(无)'}")


def show_history():
    """显示当前会话历史"""
    if not current_thread_id:
        print("无活动会话")
        return
    
    history = checkpointer.get_thread_history(current_thread_id, limit=5)
    if not history:
        print("无历史记录")
        return
    
    print(f"\n会话 {current_thread_id} 的最近记录:")
    for i, item in enumerate(history, 1):
        values = item.get("channel_values", {})
        request = values.get("user_request", "N/A")
        result = values.get("execution_result", "N/A")
        print(f"  [{i}] 请求: {request[:30]}... -> 结果: {str(result)[:30]}...")


async def interactive_mode():
    """交互模式"""
    global current_thread_id
    
    print_banner()
    init_connections()
    atexit.register(close_connections)
    
    # 显示已有会话
    existing_threads = checkpointer.list_threads()
    if existing_threads:
        print(f"\n已有会话: {existing_threads}")
    
    # 让用户输入会话 ID
    print("\n请输入会话 ID (直接回车创建新会话):")
    user_thread_id = input(">>> ").strip()
    
    if user_thread_id:
        current_thread_id = user_thread_id
        # 检查是否为已存在的会话
        if user_thread_id in existing_threads:
            print(f"恢复已有会话: {current_thread_id}")
        else:
            print(f"创建新会话: {current_thread_id}")
    else:
        current_thread_id = new_session()
        print(f"自动创建会话: {current_thread_id}")
    
    print("\n" + "=" * 50)
    print("  交互模式已启动")
    print(f"  当前会话: {current_thread_id}")
    print("  命令: new(新会话), session(会话信息), history(历史)")
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
                tools = tool_registry.list_tools()
                files = tool_registry.list_tool_files()
                print(f"\n数据库中的工具: {tools if tools else '(无)'}")
                print(f"工具文件目录: {TOOLS_DIR}")
                print(f"工具文件列表: {files if files else '(无)'}")
                continue
            
            if user_input.lower() == 'new':
                # 创建新会话
                current_thread_id = new_session()
                print(f"\n新会话已创建: {current_thread_id}")
                continue
            
            if user_input.lower() == 'session':
                # 显示会话信息
                show_session_info()
                continue
            
            if user_input.lower() == 'history':
                # 显示历史
                show_history()
                continue
            
            await run_demo(user_input, current_thread_id)
            
        except KeyboardInterrupt:
            print("\n\n中断，再见!")
            break
        except Exception as e:
            import traceback
            print(f"\n错误: {e}")
            traceback.print_exc()


async def main():
    """主函数"""
    await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
