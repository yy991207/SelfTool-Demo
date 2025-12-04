# SelfTool Demo - LLM 动态工具生成

> 基于 LangGraph 的 LLM 动态工具生成演示项目

## 项目概述

**核心功能**: 用户提出需求（如"现在几点了"），LLM 自动生成对应的 Python 函数，在沙箱中执行后返回结果。

**技术栈**:
- Python 3.10
- LangGraph 0.6.7
- MongoDB (工具持久化存储)
- Redis (工具缓存)
- 阿里云 DashScope API (LLM)

## 目录结构

```
SelfTool-Demo/
├── src/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── state.py               # 状态定义
│   ├── nodes.py               # 节点实现
│   ├── routing.py             # 路由逻辑
│   ├── graph.py               # 子图组装
│   ├── safety.py              # 安全检查
│   ├── sandbox.py             # 沙箱执行
│   ├── registry.py            # 工具注册 (MongoDB)
│   └── cache.py               # 缓存管理 (Redis)
├── tests/
│   └── test_demo.py           # 测试用例
├── .env                       # 环境变量
├── requirements.txt           # 依赖
├── main.py                    # 入口文件
└── README.md
```

## 环境准备

### 1. 创建 Conda 环境

```powershell
# 创建环境
conda create -n selftool python=3.10 -y

# 激活环境
conda activate selftool
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 启动 MongoDB 和 Redis

**方式一: Docker (推荐)**
```powershell
# MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:latest

# Redis
docker run -d --name redis -p 6379:6379 redis:latest
```

**方式二: 本地安装**
- MongoDB: https://www.mongodb.com/try/download/community
- Redis: https://github.com/microsoftarchive/redis/releases

### 4. 配置环境变量

创建 `.env` 文件:
```env
# LLM API
DASHSCOPE_API_KEY=sk-56c7427bd02243b5808da837d80ef6af
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=selftool

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## 运行演示

```powershell
# 激活环境
conda activate selftool

# 运行
python main.py
```

## 预期结果

```
用户请求: 现在几点了？

[1/6] 需求分析...
  任务描述: 获取当前系统时间

[2/6] 工具检索...
  未找到匹配工具，准备生成

[3/6] 代码生成...
  生成工具: get_current_time (v1)

[4/6] 安全检查...
  检查通过

[5/6] 沙箱执行...
  执行成功 (2ms)

[6/6] 工具注册...
  工具已注册并持久化

=====================================
执行结果: 2025-12-03 17:30:45
工具已缓存: True
=====================================
```

## 核心流程

```
用户请求 → 需求分析 → 工具检索 ─┬→ 使用已有工具 → 返回结果
                              │
                              └→ 代码生成 ←──────┐
                                    ↓           │
                               安全检查 ──失败───┤ (最多3次)
                                    ↓ 通过      │
                               沙箱执行 ──失败───┘
                                    ↓ 成功
                               工具注册 → 返回结果
```
