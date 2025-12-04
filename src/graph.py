"""子图组装模块 - 支持多任务"""

from langgraph.graph import StateGraph, START, END
from .state import SelfToolState
from .nodes import (
    analyze_requirement_node,
    plan_tasks_node,
    prepare_current_task_node,
    search_tool_node,
    generate_code_node,
    safety_check_node,
    execute_node,
    register_tool_node,
    use_existing_tool_node,
    save_task_result_node,
    aggregate_results_node,
    format_response_node,
    reject_node,
    fail_node,
)
from .routing import (
    route_after_analyze,
    route_after_search,
    route_after_safety,
    route_after_execute,
    route_after_save_result,
)


def create_self_tool_graph():
    """创建 Self-Tool 动态工具生成子图 (支持多任务)"""
    
    builder = StateGraph(SelfToolState)
    
    # 添加节点
    builder.add_node("analyze", analyze_requirement_node)
    builder.add_node("plan_tasks", plan_tasks_node)
    builder.add_node("prepare_task", prepare_current_task_node)
    builder.add_node("search", search_tool_node)
    builder.add_node("generate", generate_code_node)
    builder.add_node("safety_check", safety_check_node)
    builder.add_node("execute", execute_node)
    builder.add_node("register", register_tool_node)
    builder.add_node("use_existing", use_existing_tool_node)
    builder.add_node("save_result", save_task_result_node)
    builder.add_node("aggregate", aggregate_results_node)
    builder.add_node("format_response", format_response_node)
    builder.add_node("reject", reject_node)
    builder.add_node("fail", fail_node)
    
    # ===== 入口 =====
    builder.add_edge(START, "analyze")
    
    # 分析后分支: 需要工具 -> 任务规划, 不需要 -> 直接结束
    builder.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {
            "need_tool": "plan_tasks",
            "direct_answer": END
        }
    )
    
    # ===== 多任务循环 =====
    # 任务规划 -> 准备任务
    builder.add_edge("plan_tasks", "prepare_task")
    
    # 准备任务 -> 检索
    builder.add_edge("prepare_task", "search")
    
    # 检索后分支
    builder.add_conditional_edges(
        "search",
        route_after_search,
        {
            "use_existing": "use_existing",
            "generate": "generate"
        }
    )
    
    # 生成 -> 安全检查
    builder.add_edge("generate", "safety_check")
    
    # 安全检查后分支
    builder.add_conditional_edges(
        "safety_check",
        route_after_safety,
        {
            "execute": "execute",
            "regenerate": "generate",
            "reject": "reject"
        }
    )
    
    # 执行后分支
    builder.add_conditional_edges(
        "execute",
        route_after_execute,
        {
            "register": "register",
            "regenerate": "generate",
            "fail": "fail"
        }
    )
    
    # 注册/使用已有 -> 保存结果
    builder.add_edge("register", "save_result")
    builder.add_edge("use_existing", "save_result")
    
    # 保存结果后分支: 还有任务 -> 准备下一个, 否则 -> 汇总
    builder.add_conditional_edges(
        "save_result",
        route_after_save_result,
        {
            "next_task": "prepare_task",
            "aggregate": "aggregate"
        }
    )
    
    # 汇总 -> 润色
    builder.add_edge("aggregate", "format_response")
    
    # ===== 终点 =====
    builder.add_edge("format_response", END)
    builder.add_edge("reject", END)
    builder.add_edge("fail", END)
    
    return builder.compile()


# 导出图实例
self_tool_graph = create_self_tool_graph()
