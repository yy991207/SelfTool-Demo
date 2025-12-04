# SelfTool-Demo 执行逻辑分析

## 项目概述

这是一个基于 LangGraph 的 LLM 动态工具生成系统，能够根据用户请求自动分析需求、生成代码、安全检查、执行并注册工具。

## 技术栈

- **框架**: LangGraph (状态图编排)
- **LLM**: 阿里云 DashScope (通过 langchain_openai)
- **存储**: MongoDB (工具持久化)
- **缓存**: Redis (工具缓存)
- **执行**: 沙箱安全执行器

---

## 入口文件 `main.py`

### 启动流程

```
main() -> interactive_mode() -> run_demo(user_request)
```

1. **`print_banner()`**: 打印欢迎横幅
2. **`check_connections()`**: 检查 MongoDB 和 Redis 连接状态
3. **`interactive_mode()`**: 启动交互式命令行，支持以下命令:
   - 用户请求: 触发工具生成流程
   - `exit/quit/q`: 退出程序
   - `clear`: 清除工具缓存
   - `list`: 列出已注册工具

### 核心执行函数 `run_demo()`

```python
state = create_initial_state(user_request)  # 初始化状态
result = await self_tool_graph.ainvoke(state)  # 运行状态图
```

---

## 状态定义 `src/state.py`

### `SelfToolState` 结构

| 分组 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 输入 | `user_request` | str | 用户原始请求 |
| | `task_description` | str | 任务描述 |
| | `task_category` | str | 任务分类 |
| | `need_tool` | bool | 是否需要工具 |
| 多任务 | `task_list` | List[dict] | 子任务列表 |
| | `current_task_index` | int | 当前任务索引 |
| | `task_results` | List[dict] | 任务执行结果 |
| 检索 | `existing_tools` | List[str] | 已有工具列表 |
| | `matched_tool` | ToolSpec | 匹配到的工具 |
| | `need_generate` | bool | 是否需要生成 |
| 生成 | `generated_spec` | ToolSpec | 生成的工具规格 |
| | `generation_attempt` | int | 生成尝试次数 |
| | `generation_feedback` | str | 生成反馈 |
| 安全 | `safety_status` | Literal | pending/passed/failed |
| | `safety_issues` | List[str] | 安全问题列表 |
| 执行 | `execution_result` | str | 执行结果 |
| | `execution_error` | str | 执行错误 |
| | `execution_time_ms` | int | 执行耗时 |
| 注册 | `tool_registered` | bool | 是否已注册 |
| | `tool_cached` | bool | 是否已缓存 |
| | `tool_file` | str | 工具文件路径 |

---

## 状态图 `src/graph.py`

### 节点列表

| 节点 | 函数 | 说明 |
|------|------|------|
| analyze | `analyze_requirement_node` | 需求分析 |
| plan_tasks | `plan_tasks_node` | 任务规划 |
| prepare_task | `prepare_current_task_node` | 准备当前任务 |
| search | `search_tool_node` | 工具检索 |
| generate | `generate_code_node` | 代码生成 |
| safety_check | `safety_check_node` | 安全检查 |
| execute | `execute_node` | 沙箱执行 |
| register | `register_tool_node` | 工具注册 |
| use_existing | `use_existing_tool_node` | 使用已有工具 |
| save_result | `save_task_result_node` | 保存任务结果 |
| aggregate | `aggregate_results_node` | 汇总结果 |
| format_response | `format_response_node` | 润色回复 |
| reject | `reject_node` | 拒绝 |
| fail | `fail_node` | 失败 |

### 执行流程图

```
START
  │
  ▼
[analyze] ──────────────────────────────────────┐
  │                                              │
  │ need_tool                           direct_answer
  ▼                                              │
[plan_tasks]                                     │
  │                                              │
  ▼                                              │
[prepare_task] ◄────────────────┐               │
  │                              │               │
  ▼                              │               │
[search]                         │               │
  │                              │               │
  ├─ use_existing ──► [use_existing]             │
  │                       │      │               │
  │                       ▼      │               │
  └─ generate ──► [generate]     │               │
                      │          │               │
                      ▼          │               │
                [safety_check]   │               │
                      │          │               │
     ┌────────────────┼──────────┤               │
     │                │          │               │
   reject         execute    regenerate          │
     │                │          │               │
     ▼                ▼          │               │
 [reject]        [execute]       │               │
     │                │          │               │
     │       ┌────────┼──────────┤               │
     │       │        │          │               │
     │    fail     register   regenerate         │
     │       │        │          │               │
     │       ▼        ▼          │               │
     │    [fail]  [register]     │               │
     │       │        │          │               │
     │       │        └──────────┼───────────────┤
     │       │                   │               │
     │       │                   ▼               │
     │       │            [save_result]          │
     │       │                   │               │
     │       │        ┌─────────┴─────────┐     │
     │       │        │                   │     │
     │       │   next_task            aggregate │
     │       │        │                   │     │
     │       │        └───────┘           ▼     │
     │       │                      [aggregate]  │
     │       │                            │     │
     │       │                            ▼     │
     │       │                    [format_response]
     │       │                            │     │
     └───────┴────────────────────────────┴─────┘
                          │
                          ▼
                         END
```

---

## 路由逻辑 `src/routing.py`

| 路由函数 | 输入条件 | 输出 |
|---------|---------|------|
| `route_after_analyze` | `need_tool=True` | need_tool |
| | `need_tool=False` | direct_answer |
| `route_after_search` | `matched_tool` 存在 | use_existing |
| | `matched_tool` 不存在 | generate |
| `route_after_safety` | `safety_status=passed` | execute |
| | 重试次数未达上限 | regenerate |
| | 重试次数已达上限 | reject |
| `route_after_execute` | `execution_error=None` | register |
| | 重试次数未达上限 | regenerate |
| | 重试次数已达上限 | fail |
| `route_after_save_result` | 还有剩余任务 | next_task |
| | 任务全部完成 | aggregate |

---

## 核心模块说明

### 工具注册 `src/registry.py`

- **MongoDB 存储**: 持久化工具元信息和代码
- **文件存储**: 保存为 `tools/*.py` 文件
- **语义搜索**: 基于关键词匹配已有工具

### 缓存管理 `src/cache.py`

- **Redis 缓存**: 加速工具检索
- **TTL 过期**: 缓存自动过期机制
- **降级策略**: Redis 不可用时禁用缓存

### 安全检查 `src/safety.py`

检查规则:
1. 禁止导入: `os`, `subprocess`, `sys`
2. 禁止函数: `open`, `eval`, `exec`
3. AST 语法检查

### 沙箱执行 `src/sandbox.py`

- **受限环境**: 只允许安全模块
- **允许模块**: `datetime`, `time`, `calendar`, `math`, `json`, `re`, `random`, `string`

---

## 典型执行路径

### 路径1: 需要生成新工具

```
analyze -> plan_tasks -> prepare_task -> search -> generate 
-> safety_check -> execute -> register -> save_result 
-> aggregate -> format_response -> END
```

### 路径2: 复用已有工具

```
analyze -> plan_tasks -> prepare_task -> search -> use_existing 
-> save_result -> aggregate -> format_response -> END
```

### 路径3: 直接回答(不需要工具)

```
analyze -> END
```

### 路径4: 多任务循环

```
analyze -> plan_tasks -> prepare_task -> ... -> save_result 
-> prepare_task (循环) -> ... -> save_result -> aggregate -> format_response -> END
```

---

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 代码生成失败 | 重试生成 (最多 N 次) |
| 安全检查失败 | 反馈问题，重试生成 |
| 执行失败 | 反馈错误，重试生成 |
| 达到最大重试 | 进入 reject/fail 节点 |
| MongoDB/Redis 不可用 | 降级到内存存储/禁用缓存 |
