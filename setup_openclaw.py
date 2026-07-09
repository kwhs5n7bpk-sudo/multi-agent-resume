#!/usr/bin/env python3
"""
多Agent系统 OpenClaw 部署脚本
将多Agent系统部署到 OpenClaw 平台

用法：
    python3 setup_openclaw.py                    # 交互式安装
    python3 setup_openclaw.py --auto             # 全自动安装
    python3 setup_openclaw.py --dir /path/to     # 指定安装目录
"""
import os
import sys
import json
import argparse
from pathlib import Path


# ============================================================
# OpenClaw 配置文件
# ============================================================

OPENCLAW_CONFIG = """# OpenClaw 多Agent系统配置
# 文档: https://docs.openclaw.ai

# === 基础配置 ===
name: "multi-agent-system"
version: "1.0.0"
description: "多Agent协作系统 - 老k中枢调度"

# === 模型配置 ===
model:
  provider: "openai_compatible"
  api_base: "${LLM_BASE_URL:-https://api.openai.com/v1}"
  api_key: "${LLM_API_KEY}"
  model_id: "${LLM_MODEL:-glm-5.2}"
  temperature: 0.3
  max_tokens: 4096

# === 渠道配置 ===
channels:
  - type: "wechat"
    enabled: true
    config:
      adapter: "${WECHAT_ADAPTER:-wxauto}"
      bot_name: "老k助手"

  - type: "web"
    enabled: true
    port: 8080

# === 技能配置 ===
skills:
  - name: "rag-search"
    description: "向量检索知识库"
    enabled: true

  - name: "wiki-query"
    description: "知识图谱查询"
    enabled: true

  - name: "code-executor"
    description: "执行代码和Shell命令"
    enabled: true

  - name: "file-manager"
    description: "文件读写管理"
    enabled: true

  - name: "web-search"
    description: "网络搜索"
    enabled: true

# === Agent配置 ===
agents:
  # 主Agent - 老k
  - id: "lao-k"
    name: "老k"
    role: "primary"
    description: "中枢调度Agent，负责任务拆解、角色调度、结果汇总"
    system_prompt: |
      你是老k，多Agent系统的中枢调度者。

      ## 核心职责
      1. 接收用户需求，分析意图
      2. 拆解任务为子任务
      3. 调度合适的Agent执行
      4. 汇总结果并反馈给用户

      ## 调度规则
      - 需求分析 → 产品PM
      - UI设计 → UI设计师
      - 前端开发 → 前端工程师
      - 后端开发 → 后端工程师
      - 测试验证 → 测试工程师
      - 部署运维 → 运维工程师

      ## 可调用的子Agent
      - product: 产品PM，负责需求分析和PRD撰写
      - ui: UI设计师，负责页面设计和交互规范
      - frontend: 前端工程师，负责React/Vue组件开发
      - backend: 后端工程师，负责API和业务逻辑
      - tester: 测试工程师，负责测试和质量保障
      - ops: 运维工程师，负责CI/CD和部署

      ## 输出规范
      - 每次调度说明原因
      - 汇总结果要结构化
      - 遇到问题及时反馈
    skills:
      - "rag-search"
      - "wiki-query"
      - "web-search"
      - "file-manager"
    subagents:
      - "product"
      - "ui"
      - "frontend"
      - "backend"
      - "tester"
      - "ops"

  # 子Agent - 产品PM
  - id: "product"
    name: "产品PM"
    role: "subagent"
    description: "需求分析、PRD撰写"
    system_prompt: |
      你是产品PM，负责需求分析和PRD撰写。

      ## 职责
      - 分析用户需求
      - 撰写PRD文档
      - 定义用户故事和验收标准

      ## 输出格式
      # 功能名称
      ## 背景与目标
      ## 用户故事
      ## 功能描述
      ## 验收标准
    skills:
      - "rag-search"
      - "web-search"
      - "file-manager"

  # 子Agent - UI设计师
  - id: "ui"
    name: "UI设计师"
    role: "subagent"
    description: "页面设计和交互规范"
    system_prompt: |
      你是UI设计师，负责页面设计和交互规范。

      ## 职责
      - 设计页面布局
      - 定义组件规范
      - 输出Design Token
    skills:
      - "rag-search"
      - "file-manager"

  # 子Agent - 前端工程师
  - id: "frontend"
    name: "前端工程师"
    role: "subagent"
    description: "React/Vue组件开发"
    system_prompt: |
      你是前端工程师，负责组件和页面实现。

      ## 职责
      - 实现UI组件
      - 对接后端API
      - 优化前端性能

      ## 技术栈
      - React / Next.js / Vue
      - Tailwind CSS
      - TypeScript
    skills:
      - "code-executor"
      - "file-manager"
      - "rag-search"

  # 子Agent - 后端工程师
  - id: "backend"
    name: "后端工程师"
    role: "subagent"
    description: "API和业务逻辑开发"
    system_prompt: |
      你是后端工程师，负责API和业务逻辑。

      ## 职责
      - 设计API接口
      - 实现业务逻辑
      - 数据库设计

      ## 技术栈
      - Node.js / Python / Go
      - RESTful API
      - SQL / NoSQL
    skills:
      - "code-executor"
      - "file-manager"
      - "rag-search"

  # 子Agent - 测试工程师
  - id: "tester"
    name: "测试工程师"
    role: "subagent"
    description: "测试和质量保障"
    system_prompt: |
      你是测试工程师，负责测试和质量保障。

      ## 职责
      - 编写测试用例
      - 执行测试
      - 输出测试报告

      ## 报告格式
      - 通过: X个
      - 失败: X个
      - 失败详情
    skills:
      - "code-executor"
      - "file-manager"
      - "rag-search"

  # 子Agent - 运维工程师
  - id: "ops"
    name: "运维工程师"
    role: "subagent"
    description: "CI/CD和部署"
    system_prompt: |
      你是运维工程师，负责部署和运维。

      ## 职责
      - 编写CI/CD配置
      - Docker部署
      - 监控配置

      ## 技术栈
      - Docker / Kubernetes
      - GitHub Actions / GitLab CI
      - Nginx / Caddy
    skills:
      - "code-executor"
      - "file-manager"
      - "rag-search"

# === 安全配置 ===
security:
  # 沙箱模式
  sandbox: true
  # 允许的工具
  allowed_tools:
    - "read"
    - "write"
    - "edit"
    - "bash"
    - "glob"
    - "grep"
  # 禁止的命令
  denied_commands:
    - "rm -rf /"
    - "sudo rm"
    - "dd if="
    - "mkfs"
  # 文件系统限制
  filesystem:
    allowed_paths:
      - "./src"
      - "./docs"
      - "./tests"
    denied_paths:
      - "/etc"
      - "/var"
      - "~/.ssh"

# === 日志配置 ===
logging:
  level: "info"
  format: "json"
  output: "file"
  file: "./logs/openclaw.log"

# === 监控配置 ===
monitoring:
  enabled: true
  port: 9090
  metrics:
    - "agent_calls"
    - "token_usage"
    - "latency"
    - "errors"
"""

# Agent 定义文件（OpenClaw 格式）
AGENT_FILES = {
    "agents/lao-k.md": """---
id: lao-k
name: 老k
role: primary
description: 中枢调度Agent，负责任务拆解、角色调度、结果汇总
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.3
skills:
  - rag-search
  - wiki-query
  - web-search
  - file-manager
subagents:
  - product
  - ui
  - frontend
  - backend
  - tester
  - ops
permission:
  edit: ask
  bash: ask
  task:
    '*': deny
    product: allow
    ui: allow
    frontend: allow
    backend: allow
    tester: allow
    ops: allow
---

你是老k，多Agent系统的中枢调度者。

## 核心职责
1. 接收用户需求，分析意图
2. 拆解任务为子任务
3. 调度合适的Agent执行
4. 汇总结果并反馈给用户

## 调度规则
- 需求分析 → 产品PM
- UI设计 → UI设计师
- 前端开发 → 前端工程师
- 后端开发 → 后端工程师
- 测试验证 → 测试工程师
- 部署运维 → 运维工程师

## 输出规范
- 每次调度说明原因
- 汇总结果要结构化
- 遇到问题及时反馈
""",

    "agents/product.md": """---
id: product
name: 产品PM
role: subagent
description: 需求分析、PRD撰写
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.3
skills:
  - rag-search
  - web-search
  - file-manager
permission:
  edit:
    '*.md': allow
    '*': deny
  bash: deny
  task: deny
---

你是产品PM，负责需求分析和PRD撰写。

## 职责
- 分析用户需求
- 撰写PRD文档
- 定义用户故事和验收标准

## 输出格式
# 功能名称
## 背景与目标
## 用户故事
## 功能描述
## 验收标准
""",

    "agents/ui.md": """---
id: ui
name: UI设计师
role: subagent
description: 页面设计和交互规范
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.4
skills:
  - rag-search
  - file-manager
permission:
  edit:
    '*.md': allow
    '*': deny
  bash: deny
  task: deny
---

你是UI设计师，负责页面设计和交互规范。

## 职责
- 设计页面布局
- 定义组件规范
- 输出Design Token
""",

    "agents/frontend.md": """---
id: frontend
name: 前端工程师
role: subagent
description: React/Vue组件开发
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.2
skills:
  - code-executor
  - file-manager
  - rag-search
permission:
  edit:
    'src/**': allow
    'package.json': allow
    '*': ask
  bash:
    'npm *': allow
    'yarn *': allow
    '*': ask
  task: deny
---

你是前端工程师，负责组件和页面实现。

## 职责
- 实现UI组件
- 对接后端API
- 优化前端性能

## 技术栈
- React / Next.js / Vue
- Tailwind CSS
- TypeScript
""",

    "agents/backend.md": """---
id: backend
name: 后端工程师
role: subagent
description: API和业务逻辑开发
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.2
skills:
  - code-executor
  - file-manager
  - rag-search
permission:
  edit:
    'src/**': allow
    '*.sql': allow
    '*': ask
  bash:
    'npm *': allow
    'python *': allow
    '*': ask
  task: deny
---

你是后端工程师，负责API和业务逻辑。

## 职责
- 设计API接口
- 实现业务逻辑
- 数据库设计

## 技术栈
- Node.js / Python / Go
- RESTful API
- SQL / NoSQL
""",

    "agents/tester.md": """---
id: tester
name: 测试工程师
role: subagent
description: 测试和质量保障
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.2
skills:
  - code-executor
  - file-manager
  - rag-search
permission:
  edit:
    '**/*.test.*': allow
    '**/*.spec.*': allow
    '*': deny
  bash:
    'npm test': allow
    'npx jest*': allow
    '*': ask
  task: deny
---

你是测试工程师，负责测试和质量保障。

## 职责
- 编写测试用例
- 执行测试
- 输出测试报告

## 报告格式
- 通过: X个
- 失败: X个
- 失败详情
""",

    "agents/ops.md": """---
id: ops
name: 运维工程师
role: subagent
description: CI/CD和部署
model: ${LLM_MODEL:-glm-5.2}
temperature: 0.2
skills:
  - code-executor
  - file-manager
  - rag-search
permission:
  edit:
    'Dockerfile': allow
    'docker-compose*.yml': allow
    '.github/**': allow
    '*': ask
  bash:
    'docker ps': allow
    'docker images': allow
    '*': ask
  task: deny
---

你是运维工程师，负责部署和运维。

## 职责
- 编写CI/CD配置
- Docker部署
- 监控配置

## 技术栈
- Docker / Kubernetes
- GitHub Actions / GitLab CI
- Nginx / Caddy
""",
}

# 技能定义
SKILL_FILES = {
    "skills/rag-search/SKILL.md": """---
name: rag-search
description: 向量检索知识库，支持语义搜索和精确匹配
---

## RAG Search

使用向量数据库进行语义检索。

### 使用方法
```python
from engine.rag_engine import RAGEngine

rag = RAGEngine(persist_dir="./knowledge_db")
results = rag.search("collection_name", "查询内容", top_k=5)
```

### 支持的操作
- `search`: 语义搜索
- `write`: 写入文档
- `delete`: 删除文档
""",

    "skills/wiki-query/SKILL.md": """---
name: wiki-query
description: 知识图谱查询，支持实体关系分析和推理
---

## Wiki Query

使用知识图谱进行关系分析。

### 使用方法
```python
from engine.wiki_engine import LLMWikiEngine

wiki = LLMWikiEngine(graph_path="./knowledge_graph.json")
results = wiki.query("查询内容")
```

### 支持的操作
- `query`: 查询实体关系
- `write`: 写入实体和关系
- `stats`: 获取统计信息
""",

    "skills/code-executor/SKILL.md": """---
name: code-executor
description: 安全执行代码和Shell命令
---

## Code Executor

在沙箱中安全执行代码。

### 安全策略
- 禁止执行危险命令（rm -rf, sudo等）
- 文件系统访问受限
- 网络访问受限

### 支持的语言
- Python
- Node.js
- Shell (受限)
""",

    "skills/file-manager/SKILL.md": """---
name: file-manager
description: 文件读写管理
---

## File Manager

安全的文件操作。

### 支持的操作
- 读取文件
- 写入文件
- 列出目录
- 搜索文件

### 权限控制
- 只能访问项目目录
- 不能访问系统文件
""",

    "skills/web-search/SKILL.md": """---
name: web-search
description: 网络搜索
---

## Web Search

搜索互联网获取信息。

### 使用场景
- 查找技术文档
- 搜索API文档
- 获取最新信息
""",
}

# Docker 配置
DOCKER_FILES = {
    "Dockerfile": """FROM node:20-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip3 install -r requirements.txt

# 安装OpenClaw
RUN curl -fsSL https://openclaw.ai/install.sh | bash

# 暴露端口
EXPOSE 8080 9090

# 启动命令
CMD ["openclaw", "start", "--config", "openclaw.yaml"]
""",

    "docker-compose.yml": """version: '3.8'

services:
  openclaw:
    build: .
    container_name: multi-agent-openclaw
    ports:
      - "8080:8080"
      - "9090:9090"
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_BASE_URL=${LLM_BASE_URL}
      - LLM_MODEL=${LLM_MODEL:-glm-5.2}
      - WECHAT_ADAPTER=${WECHAT_ADAPTER:-wxauto}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "openclaw", "health"]
      interval: 30s
      timeout: 10s
      retries: 3
""",

    ".env.example": """# === LLM配置 ===
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=glm-5.2

# === 微信配置 ===
WECHAT_ADAPTER=wxauto
BOT_NAME=老k助手

# === 企业微信（可选）===
# CORP_ID=
# CORP_SECRET=
# AGENT_ID=
# TOKEN=
# AES_KEY=

# === 安全配置 ===
SANDBOX_MODE=true
ALLOWED_PATHS=./src,./docs,./tests
""",
}

# 启动脚本
START_FILES = {
    "start.sh": """#!/bin/bash
echo "=== 启动多Agent系统 (OpenClaw) ==="

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 1. 安装依赖
echo "安装依赖..."
pip3 install -r requirements.txt 2>/dev/null

# 2. 启动OpenClaw
echo "启动OpenClaw..."
openclaw start --config openclaw.yaml

echo "=== 系统已启动 ==="
echo "Web界面: http://localhost:8080"
echo "监控面板: http://localhost:9090"
""",

    "start.bat": """@echo off
echo === 启动多Agent系统 (OpenClaw) ===

pip3 install -r requirements.txt 2>nul

openclaw start --config openclaw.yaml

echo === 系统已启动 ===
echo Web界面: http://localhost:8080
pause
""",

    "requirements.txt": """chromadb>=0.4.0
networkx>=3.1
httpx>=0.24
python-dotenv>=1.0
wxauto>=3.9.0
flask>=3.0
pyyaml>=6.0
""",
}

# 文件清单（需要从主项目复制的）
COPY_FILES = [
    "engine/rag_engine.py",
    "engine/wiki_engine.py",
    "engine/query_router.py",
    "engine/dual_engine.py",
    "wechat-bot/session_manager.py",
    "wechat-bot/opencode_client.py",
    "wechat-bot/wechat_adapter.py",
    "wechat-bot/bot_main.py",
    "dashboard/index.html",
]


def main():
    parser = argparse.ArgumentParser(description="多Agent系统 OpenClaw 部署")
    parser.add_argument("--dir", default=".", help="安装目录")
    parser.add_argument("--auto", action="store_true", help="自动安装")
    args = parser.parse_args()

    install_dir = Path(args.dir).resolve()
    print(f"\n{'='*50}")
    print(f"  多Agent系统 OpenClaw 部署")
    print(f"  安装目录: {install_dir}")
    print(f"{'='*50}\n")

    # 创建目录结构
    dirs_needed = [
        "agents", "skills/rag-search", "skills/wiki-query",
        "skills/code-executor", "skills/file-manager", "skills/web-search",
        "engine", "wechat-bot", "dashboard", "data", "logs"
    ]
    for d in dirs_needed:
        (install_dir / d).mkdir(parents=True, exist_ok=True)

    # 写入OpenClaw配置
    config_path = install_dir / "openclaw.yaml"
    config_path.write_text(OPENCLAW_CONFIG, encoding="utf-8")
    print(f"  [配置] openclaw.yaml")

    # 写入Agent定义
    total = 0
    for rel_path, content in AGENT_FILES.items():
        file_path = install_dir / rel_path
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        total += 1
        print(f"  [Agent] {rel_path}")

    # 写入技能定义
    for rel_path, content in SKILL_FILES.items():
        file_path = install_dir / rel_path
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        total += 1
        print(f"  [Skill] {rel_path}")

    # 写入Docker配置
    for rel_path, content in DOCKER_FILES.items():
        file_path = install_dir / rel_path
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        total += 1
        print(f"  [Docker] {rel_path}")

    # 写入启动脚本
    for rel_path, content in START_FILES.items():
        file_path = install_dir / rel_path
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        total += 1
        print(f"  [Script] {rel_path}")

    # 复制引擎文件（从主项目）
    source_dir = Path(__file__).parent
    for rel_path in COPY_FILES:
        source = source_dir / rel_path
        target = install_dir / rel_path
        if source.exists():
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            total += 1
            print(f"  [Copy] {rel_path}")

    # 设置权限
    for script in ["start.sh"]:
        script_path = install_dir / script
        if script_path.exists():
            os.chmod(script_path, 0o755)

    print(f"\n{'='*50}")
    print(f"  ✅ OpenClaw 部署完成！共 {total} 个文件")
    print(f"{'='*50}")
    print(f"\n下一步：")
    print(f"  cd {install_dir}")
    print(f"  cp .env.example .env     # 配置环境变量")
    print(f"  vim .env                 # 编辑配置")
    print(f"  ./start.sh               # 启动系统")
    print(f"\nDocker 部署：")
    print(f"  docker-compose up -d     # 启动容器")
    print(f"  docker-compose logs -f   # 查看日志")


if __name__ == "__main__":
    main()
