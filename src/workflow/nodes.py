"""节点实现模块"""

import json
import time
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from ..infra.config import config
from .state import SelfToolState, ToolSpec
from ..execution.safety import CodeSafetyChecker
from ..execution.sandbox import SafeExecutor
from ..storage.registry import tool_registry
from ..storage.cache import tool_cache
from ..infra.logger import llm_logger, sandbox_logger, safety_logger, registry_logger, workflow_logger


# 初始化 LLM 客户端 (阿里云 DashScope)
llm = ChatOpenAI(
    model=config.LLM_MODEL,
    api_key=config.DASHSCOPE_API_KEY,
    base_url=config.DASHSCOPE_BASE_URL,
    temperature=0.2,
)


def _extract_json(text: str) -> dict:
    """从文本中提取 JSON"""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {}


async def plan_tasks_node(state: SelfToolState) -> dict:
    """任务规划节点: 将复合请求拆分为子任务"""
    print("\n[任务规划] 分析并拆分任务...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("任务规划节点: 拆分子任务")
    
    prompt = f"""分析用户请求，拆分为独立的可执行子任务。

用户请求: {state['user_request']}

规则:
1. 每个子任务应该是独立的、可单独执行的
2. 保持任务的执行顺序
3. 如果只有一个任务，也返回包含一个元素的列表
4. 每个任务需要明确的描述和分类

返回 JSON:
{{
    "tasks": [
        {{"id": 1, "description": "任务描述", "category": "datetime|calendar|math|text|other"}}
    ]
}}

只返回 JSON。"""

    llm_logger.info("发送任务规划 Prompt 到 LLM")
    llm_logger.debug(f"Prompt 内容:\n{prompt}")
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    llm_logger.info("LLM 任务规划响应:")
    llm_logger.debug(f"原始响应:\n{response.content}")
    
    result = _extract_json(response.content)
    tasks = result.get("tasks", [])
    
    if not tasks:
        # 如果解析失败，创建单一任务
        tasks = [{
            "id": 1,
            "description": state["task_description"],
            "category": state["task_category"]
        }]
    
    workflow_logger.info(f"拆分为 {len(tasks)} 个子任务:")
    for t in tasks:
        workflow_logger.info(f"  [{t['id']}] {t['description']} ({t['category']})")
        print(f"  任务{t['id']}: {t['description']}")
    
    return {
        "task_list": tasks,
        "current_task_index": 0,
        "task_results": [],
        "current_node": "plan_tasks",
    }


def prepare_current_task_node(state: SelfToolState) -> dict:
    """准备当前任务: 设置 task_description 和 task_category"""
    idx = state["current_task_index"]
    tasks = state["task_list"]
    
    if idx >= len(tasks):
        return {"current_node": "prepare_task"}
    
    task = tasks[idx]
    print(f"\n[执行任务 {idx + 1}/{len(tasks)}] {task['description']}")
    workflow_logger.info(f"准备执行任务 {idx + 1}: {task['description']}")
    
    return {
        "task_description": task["description"],
        "task_category": task.get("category", "other"),
        "matched_tool": None,
        "generated_spec": None,
        "generation_attempt": 0,
        "generation_feedback": "",
        "safety_status": "pending",
        "execution_result": None,
        "execution_error": None,
        "current_node": "prepare_task",
    }


def save_task_result_node(state: SelfToolState) -> dict:
    """保存当前任务结果并移动到下一个任务"""
    idx = state["current_task_index"]
    tasks = state["task_list"]
    results = list(state.get("task_results", []))
    
    task = tasks[idx] if idx < len(tasks) else {"id": idx + 1, "description": "unknown"}
    
    result_entry = {
        "task_id": task.get("id", idx + 1),
        "description": task.get("description", ""),
        "result": state.get("execution_result", ""),
        "error": state.get("execution_error"),
        "tool_file": state.get("tool_file"),
    }
    results.append(result_entry)
    
    workflow_logger.info(f"任务 {idx + 1} 结果已保存: {result_entry['result'][:50]}...")
    
    return {
        "task_results": results,
        "current_task_index": idx + 1,
        "current_node": "save_result",
    }


def aggregate_results_node(state: SelfToolState) -> dict:
    """汇总所有任务结果"""
    print("\n[汇总] 整合所有任务结果...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("汇总节点: 整合任务结果")
    
    results = state.get("task_results", [])
    
    if not results:
        return {
            "execution_result": state.get("execution_result", ""),
            "current_node": "aggregate",
        }
    
    combined_parts = []
    for r in results:
        if r.get("error"):
            combined_parts.append(f"任务{r['task_id']}: 执行失败 - {r['error']}")
        else:
            combined_parts.append(f"任务{r['task_id']}({r['description']}): {r['result']}")
    
    combined = "\n".join(combined_parts)
    workflow_logger.info(f"汇总结果:\n{combined}")
    
    return {
        "execution_result": combined,
        "current_node": "aggregate",
    }


async def analyze_requirement_node(state: SelfToolState) -> dict:
    """节点1: 需求分析 - 判断是否需要工具"""
    print("\n[1] 需求分析...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点1: 需求分析开始")
    workflow_logger.info(f"用户请求: {state['user_request']}")
    
    # 构建历史对话上下文
    history_context = ""
    messages = state.get("messages", [])
    if messages:
        history_lines = []
        for msg in messages[-10:]:  # 最近10条消息
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            history_lines.append(f"{role}: {msg.content}")
        if history_lines:
            history_context = "历史对话:\n" + "\n".join(history_lines) + "\n\n"
    
    prompt = f"""分析以下用户请求，判断是否需要执行工具/代码来完成。

{history_context}当前请求: {state['user_request']}

判断标准:
- 需要工具: 获取时间、计算数学、生成随机数、处理数据等需要执行代码的任务
- 不需要工具: 聊天问候、问答解释、意见咨询等可以直接回复的问题

注意: 如果历史对话中有相关信息，请结合历史回答当前问题。

返回 JSON 格式:
{{
    "need_tool": true或false,
    "task_description": "简洁的任务描述",
    "task_category": "datetime|calendar|math|text|chat|other",
    "direct_answer": "如果不需要工具，这里填写直接回复内容；否则留空"
}}

只返回 JSON。"""

    llm_logger.info("发送 Prompt 到 LLM:")
    llm_logger.debug(f"Prompt 内容:\n{prompt}")
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    llm_logger.info("LLM 响应:")
    llm_logger.debug(f"原始响应:\n{response.content}")
    
    analysis = _extract_json(response.content)
    llm_logger.info(f"解析后 JSON: {json.dumps(analysis, ensure_ascii=False)}")
    
    need_tool = analysis.get("need_tool", True)
    task_desc = analysis.get("task_description", state['user_request'])
    task_cat = analysis.get("task_category", "other")
    direct_answer = analysis.get("direct_answer", "")
    
    workflow_logger.info(f"需要工具: {need_tool}")
    workflow_logger.info(f"任务描述: {task_desc}")
    workflow_logger.info(f"任务分类: {task_cat}")
    
    if need_tool:
        print(f"  需要工具: 是")
        print(f"  任务描述: {task_desc}")
    else:
        print(f"  需要工具: 否 (直接回复)")
    
    # 构建消息历史：用户请求 + 助手回复
    new_messages = [
        HumanMessage(content=state['user_request']),
        AIMessage(content=direct_answer if direct_answer else f"任务: {task_desc}")
    ]
    
    return {
        "need_tool": need_tool,
        "task_description": task_desc,
        "task_category": task_cat,
        "execution_result": direct_answer if not need_tool else None,
        "current_node": "analyze",
        "messages": new_messages
    }


async def search_tool_node(state: SelfToolState) -> dict:
    """节点2: 工具检索"""
    print("\n[2/6] 工具检索...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点2: 工具检索开始")
    
    existing = tool_registry.list_tools()
    registry_logger.info(f"已注册工具列表: {existing}")
    
    registry_logger.info(f"搜索查询: {state['task_description']}")
    registry_logger.info(f"搜索分类: {state['task_category']}")
    
    matched = tool_registry.semantic_search(
        state["task_description"], 
        state["task_category"]
    )
    
    if matched:
        registry_logger.info(f"匹配成功! 工具: {matched['name']}")
        registry_logger.debug(f"匹配工具详情: {json.dumps(matched, ensure_ascii=False, indent=2)}")
        print(f"  找到匹配工具: {matched['name']}")
        return {
            "existing_tools": existing,
            "matched_tool": matched,
            "need_generate": False,
            "current_node": "search",
        }
    else:
        registry_logger.info("未找到匹配工具，需要生成新工具")
        print("  未找到匹配工具，准备生成")
        return {
            "existing_tools": existing,
            "matched_tool": None,
            "need_generate": True,
            "current_node": "search",
        }


async def generate_code_node(state: SelfToolState) -> dict:
    """节点3: 代码生成"""
    print("\n[3/6] 代码生成...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点3: 代码生成开始")
    workflow_logger.info(f"当前尝试次数: {state['generation_attempt'] + 1}")
    
    feedback = ""
    if state["generation_feedback"]:
        feedback = f"\n上次失败原因:\n{state['generation_feedback']}\n请修正。"
        llm_logger.warning(f"重试原因: {state['generation_feedback']}")

    # 根据任务类别选择示例
    category = state.get("task_category", "other")
    if category == "math" or "计算" in state["task_description"] or "乘" in state["task_description"]:
        example = '''{
    "name": "calculate_result",
    "description": "计算数学表达式",
    "parameters": {},
    "return_type": "str",
    "category": "math",
    "code": "def calculate_result() -> str:\\n    result = 123 * 456\\n    return str(result)"
}'''
    elif category == "datetime" or "时间" in state["task_description"]:
        example = '''{
    "name": "get_current_time",
    "description": "获取当前时间",
    "parameters": {},
    "return_type": "str",
    "category": "datetime",
    "code": "def get_current_time() -> str:\\n    from datetime import datetime\\n    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')"
}'''
    else:
        example = '''{
    "name": "tool_function",
    "description": "工具描述",
    "parameters": {},
    "return_type": "str",
    "category": "other",
    "code": "def tool_function() -> str:\\n    return 'result'"
}'''

    prompt = f"""为以下任务生成 Python 工具函数。

**重要: 请根据任务描述生成对应的工具，不要照抄示例！**

任务描述: {state["task_description"]}
{feedback}

安全规则:
1. 只能使用: datetime, time, calendar, math, json, re, random, string
2. 禁止: os, subprocess, sys, open, eval, exec
3. 函数无参数，返回字符串
4. 工具名称应该反映实际功能

返回 JSON 格式示例:
{example}

请根据任务描述生成正确的工具，只返回 JSON。"""

    llm_logger.info("发送代码生成 Prompt 到 LLM")
    llm_logger.debug(f"Prompt 内容:\n{prompt}")
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    llm_logger.info("LLM 代码生成响应:")
    llm_logger.debug(f"原始响应:\n{response.content}")
    
    spec = _extract_json(response.content)
    
    if spec:
        spec["version"] = state.get("generation_attempt", 0) + 1
        llm_logger.info(f"生成工具: {spec.get('name', 'unknown')}")
        llm_logger.info(f"工具描述: {spec.get('description', '')}")
        llm_logger.info(f"工具分类: {spec.get('category', '')}")
        llm_logger.info("\n" + "=" * 40 + " 生成的代码 " + "=" * 40)
        llm_logger.info(f"\n{spec.get('code', '')}\n")
        llm_logger.info("=" * 90)
        print(f"  生成工具: {spec.get('name', 'unknown')} (v{spec['version']})")
        return {
            "generated_spec": spec,
            "generation_attempt": state["generation_attempt"] + 1,
            "current_node": "generate",
        }
    else:
        llm_logger.error("代码生成失败: JSON 解析错误")
        return {
            "generated_spec": None,
            "generation_attempt": state["generation_attempt"] + 1,
            "generation_feedback": "JSON解析失败",
            "current_node": "generate",
            "error": "代码生成格式错误"
        }


def safety_check_node(state: SelfToolState) -> dict:
    """节点4: 安全检查"""
    print("\n[4/6] 安全检查...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点4: 安全检查开始")
    
    if not state["generated_spec"]:
        safety_logger.error("无有效工具规格")
        return {
            "safety_status": "failed",
            "safety_issues": ["未生成有效的工具规格"],
            "current_node": "safety_check"
        }
    
    checker = CodeSafetyChecker()
    code = state["generated_spec"]["code"]
    
    safety_logger.info("开始检查代码安全性...")
    safety_logger.info("\n" + "-" * 40 + " 待检查代码 " + "-" * 40)
    safety_logger.info(f"\n{code}\n")
    safety_logger.info("-" * 90)
    
    safety_logger.info("检查禁止导入...")
    safety_logger.info("检查禁止函数...")
    safety_logger.info("检查 AST 结构...")
    
    issues = checker.check_all(code)
    
    if issues:
        safety_logger.warning(f"安全检查未通过! 发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            safety_logger.warning(f"  [{i}] {issue}")
        print(f"  检查未通过: {issues}")
        return {
            "safety_status": "failed",
            "safety_issues": issues,
            "generation_feedback": "安全检查失败:\n" + "\n".join(f"- {i}" for i in issues),
            "current_node": "safety_check",
        }
    else:
        safety_logger.info("安全检查通过!")
        print("  检查通过")
        return {
            "safety_status": "passed",
            "safety_issues": [],
            "current_node": "safety_check",
        }


def execute_node(state: SelfToolState) -> dict:
    """节点5: 沙箱执行"""
    print("\n[5/6] 沙箱执行...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点5: 沙箱执行开始")
    
    spec = state["generated_spec"]
    executor = SafeExecutor()
    
    sandbox_logger.info(f"准备执行工具: {spec['name']}")
    sandbox_logger.info("\n" + "-" * 40 + " 执行代码 " + "-" * 40)
    sandbox_logger.info(f"\n{spec['code']}\n")
    sandbox_logger.info("-" * 90)
    
    sandbox_logger.info("构建安全执行环境...")
    sandbox_logger.info(f"允许的模块: {executor.ALLOWED_MODULE_NAMES}")
    
    start_time = time.perf_counter()
    sandbox_logger.info("开始执行...")
    
    try:
        result = executor.execute(spec["code"], spec["name"])
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        sandbox_logger.info(f"执行成功!")
        sandbox_logger.info(f"执行耗时: {elapsed_ms:.3f}ms")
        sandbox_logger.info(f"返回结果: {result}")
        sandbox_logger.info(f"结果类型: {type(result).__name__}")
        
        print(f"  执行成功 ({elapsed_ms:.3f}ms)")
        return {
            "execution_result": str(result),
            "execution_error": None,
            "execution_time_ms": round(elapsed_ms, 3),
            "current_node": "execute",
        }
        
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        sandbox_logger.error(f"执行失败!")
        sandbox_logger.error(f"错误类型: {type(e).__name__}")
        sandbox_logger.error(f"错误信息: {e}")
        sandbox_logger.error(f"执行耗时: {elapsed_ms:.3f}ms")
        print(f"  执行失败: {e}")
        return {
            "execution_result": None,
            "execution_error": str(e),
            "execution_time_ms": elapsed_ms,
            "generation_feedback": f"执行失败: {e}",
            "current_node": "execute",
        }


def register_tool_node(state: SelfToolState) -> dict:
    """节点6: 工具注册"""
    print("\n[6/6] 工具注册...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("节点6: 工具注册开始")
    
    if state["execution_error"]:
        registry_logger.warning("执行失败，跳过注册")
        return {
            "tool_registered": False,
            "tool_cached": False,
            "tool_file": None,
            "current_node": "register"
        }
    
    spec = state["generated_spec"]
    
    registry_logger.info(f"注册工具: {spec['name']}")
    registry_logger.info(f"工具规格: {json.dumps(spec, ensure_ascii=False, indent=2)}")
    
    # 1. 保存为 Python 文件
    registry_logger.info("保存为 Python 文件...")
    file_path = tool_registry.save_as_file(spec)
    registry_logger.info(f"文件保存: {file_path}")
    print(f"  保存文件: {file_path}")
    
    # 2. 写入 MongoDB
    registry_logger.info("写入 MongoDB...")
    registered = tool_registry.register(spec)
    registry_logger.info(f"MongoDB 写入: {'成功' if registered else '失败'}")
    
    # 3. 写入 Redis 缓存
    registry_logger.info("写入 Redis 缓存...")
    cached = tool_cache.set_tool(spec)
    registry_logger.info(f"Redis 缓存: {'成功' if cached else '失败'}")
    
    status = []
    if file_path:
        status.append("已保存文件")
    if registered:
        status.append("已入库")
    if cached:
        status.append("已缓存")
    
    print(f"  工具 {spec['name']} {', '.join(status) if status else '注册失败'}")
    
    return {
        "tool_registered": registered,
        "tool_cached": cached,
        "tool_file": file_path,
        "current_node": "register",
    }


def use_existing_tool_node(state: SelfToolState) -> dict:
    """使用已有工具"""
    print("\n[使用已有工具]")
    
    tool = state["matched_tool"]
    executor = SafeExecutor()
    
    start_time = time.time()
    
    try:
        result = executor.execute(tool["code"], tool["name"])
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"  执行工具 {tool['name']}: {result} ({elapsed_ms}ms)")
        return {
            "execution_result": str(result),
            "execution_error": None,
            "execution_time_ms": elapsed_ms,
            "current_node": "use_existing",
        }
    except Exception as e:
        return {
            "execution_result": None,
            "execution_error": str(e),
            "current_node": "use_existing",
        }


async def format_response_node(state: SelfToolState) -> dict:
    """润色节点: 将工具执行结果格式化为自然语言"""
    print("\n[润色] 格式化回复...")
    workflow_logger.info("=" * 60)
    workflow_logger.info("润色节点: 格式化回复")
    
    tool_result = state.get("execution_result", "")
    user_request = state.get("user_request", "")
    task_desc = state.get("task_description", "")
    
    prompt = f"""将以下工具执行结果转化为自然、友好的回复给用户。

用户原始请求: {user_request}
任务描述: {task_desc}
工具执行结果: {tool_result}

要求:
1. 用自然语言表达结果
2. 简洁明了，不要冗长
3. 可以适当加入友好的语气

直接回复用户，不要加任何前缀或解释。"""

    llm_logger.info("发送润色 Prompt 到 LLM")
    llm_logger.debug(f"Prompt 内容:\n{prompt}")
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    formatted = response.content.strip()
    llm_logger.info(f"润色后回复: {formatted}")
    
    print(f"  润色完成")
    
    return {
        "execution_result": formatted,
        "current_node": "format_response"
    }


def reject_node(state: SelfToolState) -> dict:
    """拒绝节点"""
    print("\n[拒绝] 工具生成失败，已达到最大重试次数")
    return {"error": "工具生成失败，已达到最大重试次数"}


def fail_node(state: SelfToolState) -> dict:
    """失败节点"""
    print(f"\n[失败] 执行错误: {state['execution_error']}")
    return {"error": f"执行失败: {state['execution_error']}"}
