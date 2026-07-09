#!/usr/bin/env python3
"""
多Agent系统一键部署脚本
在目标电脑上运行此脚本即可完整部署

用法：
    python3 setup.py                    # 交互式安装
    python3 setup.py --auto             # 全自动安装（使用默认配置）
    python3 setup.py --dir /path/to     # 指定安装目录
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path


# ============================================================
# 文件清单（所有需要生成的文件）
# ============================================================

FILES = {
    # --- 架构文档 ---
    "docs/MULTI-AGENT-ARCHITECTURE.md": """# 多Agent系统架构方案
见原始文档，此处为精简版。
核心：Hub-Spoke模型，老k为唯一调度中心，6个子Agent各司其职。
""",

    # --- 双引擎代码 ---
    "engine/rag_engine.py": r'''
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional
import chromadb


class RAGEngine:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collections = {}

    def get_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        return self.collections[name]

    def write(self, collection_name: str, document: str, metadata: Dict) -> Dict:
        collection = self.get_collection(collection_name)
        content_hash = hashlib.md5(document.encode()).hexdigest()
        existing = collection.get(where={"content_hash": content_hash})
        if existing["ids"]:
            return {"status": "skipped", "reason": "duplicate"}
        chunks = self._chunk_document(document)
        ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{metadata.get('artifact_id', 'doc')}_chunk_{i}"
            collection.add(
                ids=[chunk_id], documents=[chunk],
                metadatas=[{**metadata, "content_hash": content_hash, "chunk_index": i, "created_at": datetime.utcnow().isoformat()}]
            )
            ids.append(chunk_id)
        return {"status": "success", "ids": ids}

    def search(self, collection_name: str, query: str, top_k: int = 5) -> List[Dict]:
        collection = self.get_collection(collection_name)
        results = collection.query(query_texts=[query], n_results=top_k, include=["documents", "metadatas", "distances"])
        if not results["ids"][0]: return []
        return [{"id": did, "document": doc, "metadata": meta, "score": 1 - dist}
                for did, doc, meta, dist in zip(results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0])]

    def _chunk_document(self, document: str, chunk_size: int = 512, overlap: int = 50):
        chunks, start = [], 0
        while start < len(document):
            chunks.append(document[start:start + chunk_size])
            start += chunk_size - overlap
        return chunks
''',

    "engine/wiki_engine.py": r'''
import json, os
from datetime import datetime
from typing import Optional, Dict
import networkx as nx


class LLMWikiEngine:
    def __init__(self, graph_path: str = "./knowledge_graph.json"):
        self.graph_path = graph_path
        if os.path.exists(graph_path):
            self.graph = nx.readwrite.json_graph.node_link_graph(json.load(open(graph_path)))
        else:
            self.graph = nx.DiGraph()

    def _save_graph(self):
        data = nx.readwrite.json_graph.node_link_data(self.graph)
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def write(self, document: str, metadata: dict) -> dict:
        artifact_id = metadata.get("artifact_id", f"doc_{datetime.utcnow().timestamp()}")
        import re
        entities = []
        for f_name in re.findall(r'(?:功能|模块)[：:]\s*(.+?)(?:\n|$)', document):
            entities.append({"type": "Feature", "name": f_name.strip()})
        for api in re.findall(r'(?:GET|POST|PUT|DELETE)\s+(/[\w/]+)', document):
            entities.append({"type": "API", "name": api})
        entity_ids = []
        for entity in entities:
            eid = f"{entity['type']}_{entity['name']}"
            self.graph.add_node(eid, type=entity["type"], name=entity["name"], source=artifact_id, created_at=datetime.utcnow().isoformat())
            entity_ids.append(eid)
        self._save_graph()
        return {"status": "success", "entities": entity_ids}

    def query(self, query_text: str) -> dict:
        found = []
        for nid, nd in self.graph.nodes(data=True):
            if query_text in nd.get("name", ""):
                found.append({"id": nid, "type": nd.get("type"), "name": nd.get("name")})
        related, rels = [], []
        for e in found:
            for nb in self.graph.neighbors(e["id"]):
                nd = self.graph.nodes[nb]
                related.append({"id": nb, "type": nd.get("type"), "name": nd.get("name"), "relation": self.graph.edges[e["id"], nb].get("type")})
            for pred in self.graph.predecessors(e["id"]):
                pd = self.graph.nodes[pred]
                related.append({"id": pred, "type": pd.get("type"), "name": pd.get("name"), "relation": self.graph.edges[pred, e["id"]].get("type")})
        return {"entities": found, "related_entities": related}

    def stats(self) -> dict:
        return {"nodes": self.graph.number_of_nodes(), "edges": self.graph.number_of_edges()}
''',

    "engine/query_router.py": r'''
import re
from typing import Dict


class QueryClassifier:
    def classify(self, query: str) -> str:
        rag_kw = ['找到', '什么是', '搜索', '查找', '列出', '获取', '文档', '代码']
        wiki_kw = ['依赖', '影响', '为什么', '关系', '修改', '属于', '架构', '分析']
        for kw in rag_kw:
            if kw in query: return "rag"
        for kw in wiki_kw:
            if kw in query: return "wiki"
        return "hybrid"


class QueryRouter:
    def __init__(self, rag_engine, wiki_engine):
        self.rag = rag_engine
        self.wiki = wiki_engine
        self.classifier = QueryClassifier()

    def route(self, query: str) -> Dict:
        qt = self.classifier.classify(query)
        if qt == "rag":
            return {"type": "rag", "results": self.rag.search("documents", query)}
        elif qt == "wiki":
            return {"type": "wiki", "results": self.wiki.query(query)}
        else:
            return {"type": "hybrid", "rag": self.rag.search("documents", query), "wiki": self.wiki.query(query)}
''',

    "engine/dual_engine.py": r'''
import os
from rag_engine import RAGEngine
from wiki_engine import LLMWikiEngine
from query_router import QueryRouter


class DualKnowledgeEngine:
    def __init__(self, persist_dir: str = "./knowledge_db"):
        self.rag = RAGEngine(persist_dir=persist_dir)
        self.wiki = LLMWikiEngine(graph_path=f"{persist_dir}/knowledge_graph.json")
        self.router = QueryRouter(self.rag, self.wiki)

    def write(self, collection: str, document: str, metadata: dict) -> dict:
        return {"rag": self.rag.write(collection, document, metadata), "wiki": self.wiki.write(document, metadata)}

    def query(self, query_text: str) -> dict:
        return self.router.route(query_text)
''',

    # --- 微信Bot桥接 ---
    "wechat-bot/session_manager.py": r'''
import sqlite3, threading
from datetime import datetime, timedelta
from typing import Optional, Dict


class SessionManager:
    def __init__(self, db_path: str = "./sessions.db", idle_timeout_minutes: int = 30):
        self.db_path = db_path
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self._lock = threading.Lock()
        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                wx_user_id TEXT PRIMARY KEY, opencode_session_id TEXT NOT NULL,
                title TEXT, created_at TEXT NOT NULL, last_active TEXT NOT NULL,
                status TEXT DEFAULT 'active', context_summary TEXT DEFAULT ''
            )""")

    def get_session(self, wx_user_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM sessions WHERE wx_user_id=? AND status='active'", (wx_user_id,)).fetchone()
            if row:
                last_active = datetime.fromisoformat(row[4])
                if datetime.utcnow() - last_active > self.idle_timeout:
                    self.archive_session(wx_user_id)
                    return None
                conn.execute("UPDATE sessions SET last_active=? WHERE wx_user_id=?", (datetime.utcnow().isoformat(), wx_user_id))
                return {"wx_user_id": row[0], "opencode_session_id": row[1], "title": row[2]}
        return None

    def create_session(self, wx_user_id: str, opencode_session_id: str, title: str = None) -> Dict:
        with self._lock:
            now = datetime.utcnow().isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE sessions SET status='archived' WHERE wx_user_id=? AND status='active'", (wx_user_id,))
                conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)",
                    (wx_user_id, opencode_session_id, title or f"用户-{wx_user_id}", now, now, 'active'))
            return {"wx_user_id": wx_user_id, "opencode_session_id": opencode_session_id}

    def archive_session(self, wx_user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET status='archived' WHERE wx_user_id=? AND status='active'", (wx_user_id,))

    def get_history(self, wx_user_id: str, limit: int = 10):
        with sqlite3.connect(self.db_path) as conn:
            return [{"session_id": r[0], "title": r[1], "created_at": r[2], "status": r[3]}
                    for r in conn.execute("SELECT opencode_session_id,title,created_at,status FROM sessions WHERE wx_user_id=? ORDER BY created_at DESC LIMIT ?", (wx_user_id, limit)).fetchall()]
''',

    "wechat-bot/opencode_client.py": r'''
import httpx
from typing import Dict


class OpenCodeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:4096", api_password: str = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_password:
            import base64
            self.headers["Authorization"] = "Basic " + base64.b64encode(f"opencode:{api_password}".encode()).decode()

    async def create_session(self, title: str = None) -> Dict:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{self.base_url}/session", json={"title": title}, headers=self.headers, timeout=10)
            r.raise_for_status(); return r.json()

    async def send_message(self, session_id: str, message: str, agent: str = "lao-k") -> Dict:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{self.base_url}/session/{session_id}/message",
                json={"agent": agent, "parts": [{"type": "text", "text": message}]}, headers=self.headers, timeout=120)
            r.raise_for_status(); data = r.json()
            texts = [p.get("text", "") for p in data.get("parts", []) if p.get("type") == "text"]
            return {"reply": "\n".join(texts) or "处理完成", "message_id": data.get("info", {}).get("id")}

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as c:
                return (await c.get(f"{self.base_url}/global/health", timeout=5)).status_code == 200
        except: return False
''',

    "wechat-bot/wechat_adapter.py": r'''
import os, asyncio, logging, threading
from abc import ABC, abstractmethod
from typing import Callable, Awaitable

logger = logging.getLogger("wechat")


class WeChatAdapterBase(ABC):
    def __init__(self, bot_name: str = "老k助手"):
        self.bot_name = bot_name
        self.message_handler = None

    def on_message(self, handler):
        self.message_handler = handler

    @abstractmethod
    def start(self): pass

    @abstractmethod
    async def send_message(self, user_id: str, message: str): pass

    async def send_processing(self, user_id: str):
        await self.send_message(user_id, "⏳ 处理中...")


class WxAutoAdapter(WeChatAdapterBase):
    def start(self):
        try:
            from wxauto import WeChat
            wx = WeChat()
            logger.info("wxauto启动")
            def listen():
                import time
                while True:
                    try:
                        for msg in wx.GetAllMessage():
                            if msg.type == 'friend' and msg.sender != self.bot_name:
                                if self.message_handler:
                                    reply = asyncio.run(self.message_handler(msg.sender, msg.content))
                                    wx.SendMsg(msg=reply, who=msg.sender)
                    except: pass
                    time.sleep(1)
            threading.Thread(target=listen, daemon=True).start()
        except ImportError:
            logger.error("pip install wxauto"); raise

    async def send_message(self, user_id, message):
        from wxauto import WeChat
        WeChat().SendMsg(msg=message, who=user_id)


class EnterpriseWeChatAdapter(WeChatAdapterBase):
    def __init__(self, bot_name, corp_id, corp_secret, agent_id, token, aes_key):
        super().__init__(bot_name)
        self.corp_id, self.corp_secret, self.agent_id = corp_id, corp_secret, agent_id
        self.token, self.aes_key = token, aes_key

    def start(self):
        from flask import Flask, request
        import hashlib, xml.etree.ElementTree as ET
        app = Flask(__name__)
        bot = self

        @app.route("/callback", methods=["GET", "POST"])
        def callback():
            if request.method == "GET":
                sig = request.args.get("signature",""); ts = request.args.get("timestamp",""); nc = request.args.get("nonce",""); echo = request.args.get("echostr","")
                if hashlib.sha1("".join(sorted([bot.token, ts, nc])).encode()).hexdigest() == sig: return echo
                return "err"
            root = ET.fromstring(request.data)
            fid, msg = root.find("FromUserName").text, root.find("Content").text
            if bot.message_handler:
                reply = asyncio.run(bot.message_handler(fid, msg))
                return f"<xml><ToUserName><![CDATA[{fid}]]></ToUserName><FromUserName><![CDATA[{root.find('ToUserName').text}]]></FromUserName><CreateTime>1</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[{reply}]]></Content></xml>"
            return "success"
        app.run(host="0.0.0.0", port=8080)

    async def send_message(self, user_id, message):
        import httpx
        async with httpx.AsyncClient() as c:
            t = (await c.get("https://qyapi.weixin.qq.com/cgi-bin/gettoken", params={"corpid": self.corp_id, "corpsecret": self.corp_secret})).json()["access_token"]
            await c.post(f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={t}", json={"touser": user_id, "msgtype": "text", "agentid": int(self.agent_id), "text": {"content": message}})


def create_adapter(adapter_type: str = None, **kwargs):
    adapter_type = adapter_type or os.getenv("WECHAT_ADAPTER", "wxauto")
    adapters = {"wxauto": WxAutoAdapter, "enterprise_wechat": EnterpriseWeChatAdapter}
    return adapters[adapter_type](**kwargs)
''',

    "wechat-bot/bot_main.py": r'''
import os, asyncio, logging
from dotenv import load_dotenv
from session_manager import SessionManager
from opencode_client import OpenCodeClient
from wechat_adapter import create_adapter

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("bot")


class WeChatBot:
    def __init__(self):
        self.sessions = SessionManager(db_path=os.getenv("SESSION_DB_PATH", "./sessions.db"))
        self.opencode = OpenCodeClient(base_url=os.getenv("OPENCODE_URL", "http://127.0.0.1:4096"))
        adapter_type = os.getenv("WECHAT_ADAPTER", "wxauto")
        kwargs = {"bot_name": os.getenv("BOT_NAME", "老k助手")}
        if adapter_type == "enterprise_wechat":
            kwargs.update({"corp_id": os.getenv("CORP_ID"), "corp_secret": os.getenv("CORP_SECRET"),
                           "agent_id": os.getenv("AGENT_ID"), "token": os.getenv("TOKEN"), "aes_key": os.getenv("AES_KEY")})
        self.wechat = create_adapter(adapter_type, **kwargs)
        self.wechat.on_message(self.handle_message)

    async def handle_message(self, wx_user_id: str, message: str) -> str:
        if message.strip() in ["新对话", "新会话"]:
            self.sessions.archive_session(wx_user_id)
            return "已创建新对话。"
        if message.strip() == "历史对话":
            history = self.sessions.get_history(wx_user_id)
            return "\n".join([f"{i+1}. {h['title']} ({h['created_at'][:10]})" for i, h in enumerate(history)]) or "暂无历史。"
        session = self.sessions.get_session(wx_user_id)
        if not session:
            s = await self.opencode.create_session(f"微信-{wx_user_id}")
            session = self.sessions.create_session(wx_user_id, s["id"])
        await self.wechat.send_processing(wx_user_id)
        resp = await self.opencode.send_message(session["opencode_session_id"], message)
        return resp.get("reply", "处理出错。")

    def run(self):
        logger.info(f"Bot启动 -> {self.opencode.base_url}")
        self.wechat.start()


if __name__ == "__main__":
    WeChatBot().run()
''',

    "wechat-bot/.env.example": """# OpenCode
OPENCODE_URL=http://127.0.0.1:4096
OPENCODE_PASSWORD=

# 会话
SESSION_DB_PATH=./sessions.db

# Bot
BOT_NAME=老k助手
WECHAT_ADAPTER=wxauto

# 企业微信（可选）
# CORP_ID=
# CORP_SECRET=
# AGENT_ID=
# TOKEN=
# AES_KEY=
""",

    # --- Agent定义文件 ---
    "agents/lao-k.md": """---
description: 老k - 中枢调度Agent，负责任务拆解、角色调度、结果汇总
mode: primary
permission:
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
description: 产品PM - 需求分析、PRD撰写
mode: subagent
permission:
  edit: { '*.md': allow, '*': deny }
  bash: deny
  task: deny
  webfetch: allow
  websearch: allow
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
description: UI设计师 - 页面设计和交互规范
mode: subagent
permission:
  edit: { '*.md': allow, '*': deny }
  bash: deny
  task: deny
  webfetch: allow
---

你是UI设计师，负责页面设计和交互规范。

## 职责
- 设计页面布局
- 定义组件规范
- 输出Design Token
""",

    "agents/frontend.md": """---
description: 前端工程师 - React/Vue组件开发
mode: subagent
permission:
  edit: { 'src/**': allow, 'package.json': allow, '*': ask }
  bash: { 'npm *': allow, 'yarn *': allow, '*': ask }
  task: deny
  webfetch: allow
---

你是前端工程师，负责组件和页面实现。

## 职责
- 实现UI组件
- 对接后端API
- 优化前端性能
""",

    "agents/backend.md": """---
description: 后端工程师 - API和业务逻辑开发
mode: subagent
permission:
  edit: { 'src/**': allow, '*.sql': allow, '*': ask }
  bash: { 'npm *': allow, 'python *': allow, '*': ask }
  task: deny
  webfetch: allow
---

你是后端工程师，负责API和业务逻辑。

## 职责
- 设计API接口
- 实现业务逻辑
- 数据库设计
""",

    "agents/tester.md": """---
description: 测试工程师 - 编写测试、执行测试、输出报告
mode: subagent
permission:
  edit: { '**/*.test.*': allow, '**/*.spec.*': allow, '*': deny }
  bash: { 'npm test': allow, 'npx jest*': allow, '*': ask }
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
description: 运维工程师 - CI/CD和部署
mode: subagent
permission:
  edit: { 'Dockerfile': allow, 'docker-compose*.yml': allow, '.github/**': allow, '*': ask }
  bash: { 'docker ps': allow, 'docker images': allow, '*': ask }
  task: deny
---

你是运维工程师，负责部署和运维。

## 职责
- 编写CI/CD配置
- Docker部署
- 监控配置
""",

    # --- OpenCode配置 ---
    "opencode.json": """{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "lao-k",
  "agent": {
    "lao-k": { "mode": "primary", "description": "中枢调度Agent" },
    "product": { "mode": "subagent", "description": "产品需求分析" },
    "ui": { "mode": "subagent", "description": "UI/UX设计" },
    "frontend": { "mode": "subagent", "description": "前端开发" },
    "backend": { "mode": "subagent", "description": "后端开发" },
    "tester": { "mode": "subagent", "description": "测试工程师" },
    "ops": { "mode": "subagent", "description": "运维工程师" }
  }
}
""",

    # --- 启动脚本 ---
    "start.sh": """#!/bin/bash
echo "=== 启动多Agent系统 ==="

# 1. 安装Python依赖
pip3 install -r requirements.txt 2>/dev/null

# 2. 启动OpenCode Web（后台）
echo "启动OpenCode Web..."
opencode web --port 4096 &
OPENCODE_PID=$!
sleep 3

# 3. 启动微信Bot（后台）
echo "启动微信Bot..."
cd wechat-bot && python3 bot_main.py &
BOT_PID=$!

echo ""
echo "=== 系统已启动 ==="
echo "OpenCode Web: http://localhost:4096"
echo "OpenCode PID: $OPENCODE_PID"
echo "Bot PID: $BOT_PID"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $OPENCODE_PID $BOT_PID 2>/dev/null; exit" INT TERM
wait
""",

    "start.bat": """@echo off
echo === 启动多Agent系统 ===

pip3 install -r requirements.txt 2>nul

echo 启动OpenCode Web...
start /B opencode web --port 4096
timeout /t 3

echo 启动微信Bot...
cd wechat-bot && start /B python3 bot_main.py

echo.
echo === 系统已启动 ===
echo OpenCode Web: http://localhost:4096
echo.
pause
""",

    "requirements.txt": """chromadb>=0.4.0
networkx>=3.1
httpx>=0.24
python-dotenv>=1.0
wxauto>=3.9.0
flask>=3.0
""",

    "README.md": """# 多Agent系统 - 一键部署

## 快速开始

### macOS / Linux
```bash
chmod +x start.sh
./start.sh
```

### Windows
```cmd
start.bat
```

### 手动启动
```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 启动OpenCode（端口4096）
opencode web --port 4096

# 3. 启动微信Bot
cd wechat-bot
python3 bot_main.py
```

## 访问
- OpenCode Web: http://localhost:4096
- 任务看板: 打开 dashboard/index.html

## Agent角色
| Agent | 职责 |
|-------|------|
| 老k | 中枢调度 |
| 产品PM | 需求分析 |
| UI | 界面设计 |
| 前端 | 页面开发 |
| 后端 | API开发 |
| 测试 | 质量保障 |
| 运维 | 部署运维 |
""",
}


def main():
    parser = argparse.ArgumentParser(description="多Agent系统一键部署")
    parser.add_argument("--dir", default=".", help="安装目录")
    parser.add_argument("--auto", action="store_true", help="自动安装")
    args = parser.parse_args()

    install_dir = Path(args.dir).resolve()
    print(f"\n{'='*50}")
    print(f"  多Agent系统一键部署")
    print(f"  安装目录: {install_dir}")
    print(f"{'='*50}\n")

    # 创建目录
    dirs_needed = ["docs", "engine", "wechat-bot", "agents", "dashboard"]
    for d in dirs_needed:
        (install_dir / d).mkdir(parents=True, exist_ok=True)

    # 写入文件
    total = len(FILES)
    for i, (rel_path, content) in enumerate(FILES.items(), 1):
        file_path = install_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  [{i}/{total}] {rel_path}")

    # 设置启动脚本权限
    for script in ["start.sh"]:
        script_path = install_dir / script
        if script_path.exists():
            os.chmod(script_path, 0o755)

    print(f"\n{'='*50}")
    print(f"  ✅ 部署完成！共生成 {total} 个文件")
    print(f"{'='*50}")
    print(f"\n下一步：")
    print(f"  cd {install_dir}")
    print(f"  ./start.sh        # macOS/Linux")
    print(f"  start.bat         # Windows")
    print(f"  python3 wechat-bot/bot_main.py  # 仅启动Bot")


if __name__ == "__main__":
    main()
