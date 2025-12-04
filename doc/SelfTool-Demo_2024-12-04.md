# SelfTool-Demo 连接管理器实现

## 需求描述
在 main.py 中创建数据库连接池和缓存管理器，统一管理调用方法。

## 执行计划

### 1. 创建连接管理模块 `src/connection_manager.py` [已完成]
- 实现 `DatabasePool` 类：MongoDB 连接池管理
- 实现 `CacheManager` 类：Redis 缓存连接管理
- 实现 `ConnectionManager` 类：统一管理入口（单例模式）

### 2. 修改 `main.py` [已完成]
- 导入 ConnectionManager
- 在启动时初始化连接
- 在退出时关闭连接

### 3. 更新现有模块 [已完成]
- 修改 `cache.py` 使用 ConnectionManager 获取 Redis 连接
- 修改 `registry.py` 使用 ConnectionManager 获取 MongoDB 连接

## 设计原则
- 单例模式：确保全局只有一个连接管理器实例
- 延迟连接：首次使用时建立连接
- 连接复用：避免重复创建连接
- 优雅关闭：程序退出时正确关闭所有连接

---

# Checkpoint 会话存储实现

## 需求描述
使用 checkpoint 存储当前会话记录。

## 执行计划

### 1. 创建 `src/checkpointer.py` [已完成]
- 实现 `MongoDBCheckpointer` 类：基于 MongoDB 的会话状态持久化
- 方法：`put`, `get_tuple`, `list`, `put_writes`
- 辅助方法：`get_thread_history`, `list_threads`, `delete_thread`

### 2. 修改 `src/graph.py` [已完成]
- 导入 checkpointer
- 编译图时传入 `checkpointer=checkpointer`

### 3. 修改 `main.py` [已完成]
- 添加全局 `current_thread_id` 会话标识
- 新增命令：
  - `new`: 创建新会话
  - `session`: 显示会话信息
  - `history`: 显示当前会话历史
- 每次请求带上 thread_id 配置

---

# 跨会话历史恢复

## 问题描述
重启服务后新会话无法读取老会话历史，因为每次启动都生成新的随机 thread_id。

## 解决方案 [已完成]
修改 `main.py` 的 `interactive_mode()`：
- 启动时显示已有会话列表
- 让用户输入会话 ID（可恢复已有会话或创建新会话）
- 直接回车自动生成随机 ID

---

# src 目录重构

## 目标
将 src 下的 12 个模块按功能分类，方便维护。

## 新目录结构 [已完成]

```
src/
├── infra/           # 基础设施
│   ├── config.py
│   ├── logger.py
│   └── connection_manager.py
├── storage/         # 存储层
│   ├── cache.py
│   ├── checkpointer.py
│   └── registry.py
├── workflow/        # 工作流核心
│   ├── state.py
│   ├── nodes.py
│   ├── routing.py
│   └── graph.py
└── execution/       # 执行层
    ├── safety.py
    └── sandbox.py
```

## 修改内容
1. 创建 4 个子目录并移动文件
2. 为每个子目录创建 `__init__.py` 导出模块
3. 更新所有文件的 import 路径
4. 更新 `main.py` 的 import
