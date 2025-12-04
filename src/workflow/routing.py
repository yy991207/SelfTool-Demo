"""路由逻辑模块"""

from typing import Literal
from .state import SelfToolState
from ..infra.config import config


def route_after_analyze(state: SelfToolState) -> Literal["need_tool", "direct_answer"]:
    """分析后路由: 判断是否需要工具"""
    if state.get("need_tool", True):
        return "need_tool"
    return "direct_answer"


def route_after_search(state: SelfToolState) -> Literal["use_existing", "generate"]:
    """检索后路由"""
    if state.get("matched_tool"):
        return "use_existing"
    return "generate"


def route_after_safety(state: SelfToolState) -> Literal["execute", "regenerate", "reject"]:
    """安全检查后路由"""
    if state.get("safety_status") == "passed":
        return "execute"
    elif state.get("generation_attempt", 0) < config.MAX_GENERATION_ATTEMPTS:
        return "regenerate"
    return "reject"


def route_after_execute(state: SelfToolState) -> Literal["register", "regenerate", "fail"]:
    """执行后路由"""
    if state.get("execution_error") is None:
        return "register"
    elif state.get("generation_attempt", 0) < config.MAX_GENERATION_ATTEMPTS:
        return "regenerate"
    return "fail"


def route_after_save_result(state: SelfToolState) -> Literal["next_task", "aggregate"]:
    """保存结果后路由: 判断是否还有下一个任务"""
    current = state.get("current_task_index", 0)
    total = len(state.get("task_list", []))
    
    if current < total:
        return "next_task"
    return "aggregate"


def route_after_should_continue(state: SelfToolState) -> Literal["continue", "end"]:
    """迭代判断后路由: 是否继续执行"""
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 5)
    reasoning = state.get("continue_reasoning", "")
    
    # 达到最大迭代次数
    if iteration >= max_iter:
        return "end"
    
    # 检查 [DONE] 标记（由 should_continue_node 设置）
    if reasoning.startswith("[DONE]"):
        return "end"
    
    # 未完成，继续执行
    return "continue"
