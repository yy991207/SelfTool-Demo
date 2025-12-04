"""状态定义模块"""

from typing import TypedDict, Annotated, Optional, Literal, List
from langgraph.graph.message import add_messages


class ToolSpec(TypedDict):
    """生成的工具规格"""
    name: str
    description: str
    parameters: dict
    return_type: str
    category: str
    code: str
    version: int


class SelfToolState(TypedDict):
    """Self-Tool 子图状态"""
    
    # 输入
    user_request: str
    task_description: str
    task_category: str
    need_tool: bool  # 是否需要工具
    
    # 多任务规划
    task_list: List[dict]           # 子任务列表
    current_task_index: int          # 当前任务索引
    task_results: List[dict]         # 各任务执行结果
    
    # 工具检索
    existing_tools: List[str]
    matched_tool: Optional[ToolSpec]
    need_generate: bool
    
    # 代码生成
    generated_spec: Optional[ToolSpec]
    generation_attempt: int
    generation_feedback: str
    
    # 安全检查
    safety_status: Literal["pending", "passed", "failed"]
    safety_issues: List[str]
    
    # 执行
    execution_result: Optional[str]
    execution_error: Optional[str]
    execution_time_ms: int
    
    # 注册
    tool_registered: bool
    tool_cached: bool
    tool_file: Optional[str]
    
    # 消息
    messages: Annotated[list, add_messages]
    
    # 流程控制
    current_node: str
    error: Optional[str]


def create_initial_state(user_request: str) -> SelfToolState:
    """创建初始状态"""
    return {
        "user_request": user_request,
        "task_description": "",
        "task_category": "other",
        "need_tool": True,
        "task_list": [],
        "current_task_index": 0,
        "task_results": [],
        "existing_tools": [],
        "matched_tool": None,
        "need_generate": False,
        "generated_spec": None,
        "generation_attempt": 0,
        "generation_feedback": "",
        "safety_status": "pending",
        "safety_issues": [],
        "execution_result": None,
        "execution_error": None,
        "execution_time_ms": 0,
        "tool_registered": False,
        "tool_cached": False,
        "tool_file": None,
        "messages": [],
        "current_node": "start",
        "error": None,
    }
