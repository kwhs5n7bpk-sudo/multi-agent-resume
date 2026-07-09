# Local Mesh 通讯协议：Hub-Spoke 增强方案

> 版本：v1.0 | 日期：2026-07-07

---

## 一、问题分析：严格 Hub-Spoke 的延迟瓶颈

### 1.1 五个高延迟场景

**场景 1：代码 → 审查 循环**

```
严格 Hub-Spoke（4 次中转）：
BackendAgent 写代码 → 报告老k → 老k 调 TesterAgent 审查 → 
TesterAgent 审查完 → 报告老k → 老k 调 BackendAgent 修复 → 
BackendAgent 修复完 → 报告老k → 老k 调 TesterAgent 再审 → 
TesterAgent 确认 → 报告老k

总延迟：4 × (Agent执行时间 + 老k调度时间)
假设每次 30 秒：4 × 30s = 120 秒
```

**场景 2：UI 设计 ↔ 前端实现 协商**

```
严格 Hub-Spoke（6 次中转）：
UIDesigner 设计完 → 报告老k → 老k 调 FrontendAgent → 
FrontendAgent 有疑问 → 报告老k → 老k 调 UIDesigner 答疑 → 
UIDesigner 回答 → 报告老k → 老k 调 FrontendAgent 继续 → 
FrontendAgent 实现完 → 报告老k

总延迟：6 × 30s = 180 秒
```

**场景 3：后端 API → 前端对接**

```
严格 Hub-Spoke（4 次中转）：
BackendAgent 定义 API → 报告老k → 老k 调 FrontendAgent → 
FrontendAgent 发现接口不匹配 → 报告老k → 老k 调 BackendAgent 修改 → 
BackendAgent 修改完 → 报告老k → 老k 调 FrontendAgent 继续

总延迟：4 × 30s = 120 秒
```

**场景 4：产品需求 → UI 设计 → 前端实现 三方协调**

```
严格 Hub-Spoke（6+ 次中转）：
产品写完PRD → 报告老k → 老k 调 UI → 
UI 设计完 → 报告老k → 老k 调前端 → 
前端发现PRD有歧义 → 报告老k → 老k 调产品澄清 → 
产品澄清完 → 报告老k → 老k 调UI调整 → 
UI 调整完 → 报告老k → 老k 调前端继续

总延迟：6 × 30s = 180 秒（还不算多轮澄清）
```

**场景 5：测试发现 Bug → 开发修复 → 回归验证**

```
严格 Hub-Spoke（4 次中转）：
TesterAgent 发现Bug → 报告老k → 老k 调 BackendAgent 修复 → 
BackendAgent 修复完 → 报告老k → 老k 调 TesterAgent 回归 → 
TesterAgent 验证完 → 报告老k

总延迟：4 × 30s = 120 秒
```

### 1.2 延迟根因

```
根因：老k 是唯一的通讯中枢，所有信息必须经过老k。

问题：
1. 老k 需要解析每个Agent的输出，决定下一步 → 增加调度延迟
2. 信息在传递过程中被"转述"，可能丢失细节 → 增加沟通成本
3. 每次中转都涉及Session切换 → 增加系统开销
```

---

## 二、Local Mesh 设计方案

### 2.1 核心思想

```
允许特定 Agent 对之间通过 RAG 共享状态实现"准直接通讯"，
但所有通讯必须：
1. 写入 RAG（可审计）
2. 通知老k（可监控）
3. 遵循标准协议（可解析）
```

### 2.2 架构对比

```
严格 Hub-Spoke：
┌─────┐     ┌─────┐     ┌─────┐
│Agent│ ──▶ │ 老k │ ──▶ │Agent│
│  A  │ ◀── │     │ ◀── │  B  │
└─────┘     └─────┘     └─────┘
   每次通讯必须经过老k

Local Mesh：
┌─────┐     ┌─────┐     ┌─────┐
│Agent│ ──▶ │ RAG │ ◀── │Agent│
│  A  │ ◀── │     │ ──▶ │  B  │
└──┬──┘     └──┬──┘     └──┬──┘
   │           │           │
   └───────────┼───────────┘
               ▼
            ┌─────┐
            │ 老k │（监控所有通讯）
            └─────┘
```

### 2.3 允许 Mesh 通讯的 Agent 对

| Agent A | Agent B | 通讯类型 | 原因 |
|---------|---------|---------|------|
| 后端 | 前端 | API契约 | 强依赖，需要快速迭代 |
| 后端 | 测试 | 代码→审查 | 高频循环，减少中转 |
| 前端 | 测试 | 代码→审查 | 高频循环，减少中转 |
| 产品 | UI | 需求→设计 | 需要多轮澄清 |
| UI | 前端 | 设计→实现 | 需要多轮确认 |

**不允许 Mesh 通讯的 Agent 对：**

| Agent A | Agent B | 原因 |
|---------|---------|------|
| 运维 | 任何 | 运维操作必须经过老k审批 |
| 产品 | 后端 | 跨层通讯，需要老k协调 |
| 产品 | 前端 | 跨层通讯，需要老k协调 |
| UI | 后端 | 跨层通讯，需要老k协调 |

---

## 三、通讯协议设计

### 3.1 消息格式

```json
{
  "mesh_message": {
    "id": "msg_abc123",                    // 消息唯一ID
    "trace_id": "tr_xyz789",              // 追踪ID（关联到老k的调度链）
    "from_agent": "backend",              // 发送方
    "to_agent": "frontend",               // 接收方
    "type": "api_contract | code_review | design_spec | question | answer",
    "priority": "high | medium | low",     // 优先级
    "artifact_ref": {                     // 关联的产物引用
      "collection": "api_contracts",      // RAG collection
      "id": "api_001",                    // 产物ID
      "version": "1.0.0"                  // 版本号
    },
    "message": "API设计完成，请审查",       // 摘要信息
    "requires_response": true,            // 是否需要回复
    "timeout_seconds": 300,               // 超时时间
    "created_at": "2026-07-07T10:00:00Z"
  }
}
```

### 3.2 RAG Collection 设计

```
mesh_communications/
├── api_contracts/          # 后端↔前端：API契约
│   ├── {id}/
│   │   ├── spec.json      # API规范
│   │   ├── version        # 版本号
│   │   ├── status         # draft | reviewing | approved | rejected
│   │   └── feedback[]     # 审查反馈
│
├── code_reviews/           # 开发↔测试：代码审查
│   ├── {id}/
│   │   ├── code_ref       # 代码引用
│   │   ├── review_result  # 审查结果
│   │   ├── issues[]       # 发现的问题
│   │   └── status         # pending | passed | failed
│
├── design_specs/           # UI↔前端：设计规范
│   ├── {id}/
│   │   ├── design_doc     # 设计文档
│   │   ├── questions[]    # 前端的问题
│   │   ├── answers[]      # UI的回答
│   │   └── status         # drafting | clarifying | finalized
│
├── requirements/           # 产品↔UI：需求澄清
│   ├── {id}/
│   │   ├── prd_ref        # PRD引用
│   │   ├── clarifications[] # 澄清记录
│   │   └── status         # analyzing | clarifying | confirmed
│
└── messages/               # 通用消息
    ├── {id}/
    │   ├── from_agent
    │   ├── to_agent
    │   ├── content
    │   └── status         # sent | read | responded | timeout
```

### 3.3 通讯流程（以代码审查为例）

```
第1步：后端Agent写完代码
┌─────────────────────────────────────────────────────────┐
│ BackendAgent                                            │
│                                                         │
│ 1. 完成代码编写                                          │
│ 2. 调用RAG写入接口：                                     │
│    rag_write(                                           │
│      collection="mesh_communications/code_reviews",     │
│      data={                                             │
│        "code_ref": "src/auth.ts",                       │
│        "from_agent": "backend",                         │
│        "to_agent": "tester",                            │
│        "type": "code_review",                           │
│        "message": "登录模块代码完成，请审查",              │
│        "requires_response": true                        │
│      }                                                  │
│    )                                                    │
│ 3. 返回给老k：                                          │
│    "代码完成，已提交审查请求 msg_abc123"                   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
第2步：老k收到通知，决定是否触发TesterAgent
┌─────────────────────────────────────────────────────────┐
│ 老k                                                     │
│                                                         │
│ 1. 收到后端Agent的返回消息                                │
│ 2. 解析出 msg_abc123                                     │
│ 3. 决策：                                                │
│    - 如果是高优先级 → 立即调用TesterAgent                 │
│    - 如果是低优先级 → 等待更多Agent完成后再批量处理        │
│ 4. 调用TesterAgent：                                     │
│    Task(                                                │
│      subagent_type="tester",                            │
│      prompt="请审查 msg_abc123 中的代码"                  │
│    )                                                    │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
第3步：TesterAgent从RAG读取代码并审查
┌─────────────────────────────────────────────────────────┐
│ TesterAgent                                             │
│                                                         │
│ 1. 从RAG读取代码：                                       │
│    code = rag_read("mesh_communications/code_reviews/abc123") │
│ 2. 执行审查                                              │
│ 3. 将审查结果写回RAG：                                    │
│    rag_write(                                           │
│      collection="mesh_communications/code_reviews",     │
│      id="abc123",                                       │
│      update={                                           │
│        "review_result": "通过",                          │
│        "issues": [],                                    │
│        "status": "passed"                                │
│      }                                                  │
│    )                                                    │
│ 4. 返回给老k：                                          │
│    "审查完成，结果：通过"                                  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
第4步：老k收到审查结果，决定下一步
┌─────────────────────────────────────────────────────────┐
│ 老k                                                     │
│                                                         │
│ 1. 收到TesterAgent的返回                                 │
│ 2. 解析审查结果                                          │
│ 3. 如果通过 → 继续下一步（如部署）                        │
│ 4. 如果不通过 → 调用BackendAgent修复                      │
│    Task(                                                │
│      subagent_type="backend",                           │
│      prompt="审查未通过，请修复以下问题：..."              │
│    )                                                    │
└─────────────────────────────────────────────────────────┘
```

### 3.4 对比：严格Hub-Spoke vs Local Mesh

```
场景：代码审查+修复循环

严格 Hub-Spoke（4次中转）：
Backend → 老k → Tester → 老k → Backend → 老k → Tester → 老k
总延迟：4 × (Agent执行 + 老k调度) ≈ 120秒

Local Mesh（3次中转，减少25%）：
Backend → RAG(写代码) → 老k通知 → Tester → RAG(写审查) → 老k通知 → Backend → RAG(写修复) → 老k通知
总延迟：3 × (Agent执行 + 老k调度) ≈ 90秒

节省：30秒（25%延迟减少）
```

```
场景：UI设计↔前端协商（3轮澄清）

严格 Hub-Spoke（6次中转）：
UI → 老k → Frontend → 老k → UI → 老k → Frontend → 老k → UI → 老k → Frontend → 老k
总延迟：6 × 30s = 180秒

Local Mesh（4次中转，减少33%）：
UI → RAG(设计) → 老k通知 → Frontend → RAG(问题) → 老k通知 → UI → RAG(回答) → 老k通知 → Frontend → RAG(实现) → 老k通知
总延迟：4 × 30s = 120秒

节省：60秒（33%延迟减少）
```

---

## 四、老k 的监控与仲裁

### 4.1 老k 的新职责

```
老k 不再只是"调度者"，而是"调度者 + 监控者 + 仲裁者"

职责1：调度（不变）
  - 分析任务，调用Agent

职责2：监控（新增）
  - 监听RAG中的mesh通讯消息
  - 检测超时、异常、冲突

职责3：仲裁（新增）
  - 解决Agent间的冲突
  - 调整通讯优先级
  - 必要时干预直接通讯
```

### 4.2 监控规则

```python
MESH_MONITOR_RULES = {
    # 规则1：超时检测
    "timeout": {
        "condition": "message.status == 'sent' AND now - message.created_at > message.timeout_seconds",
        "action": "notify_admin_and_retry",
        "max_retries": 2
    },
    
    # 规则2：冲突检测
    "conflict": {
        "condition": "multiple_agents_writing_same_artifact",
        "action": "pause_and_arbitrate",
        "arbitration_strategy": "priority_based"  # 按Agent优先级决定
    },
    
    # 规则3：死循环检测
    "loop": {
        "condition": "same_agents_communicating_same_topic > 5_times",
        "action": "interrupt_and_escalate_to_human",
        "threshold": 5
    },
    
    # 规则4：异常模式检测
    "anomaly": {
        "condition": "agent_response_time > 2x_average",
        "action": "log_and_alert",
        "alert_threshold": "3_consecutive"
    }
}
```

### 4.3 仲裁策略

```python
class MeshArbitrator:
    def __init__(self):
        self.priority_rules = {
            # 后端和前端关于API格式的冲突：后端优先
            ("backend", "frontend", "api_format"): "backend",
            
            # UI和前端关于设计实现的冲突：UI优先
            ("ui", "frontend", "design_impl"): "ui",
            
            # 产品和UI关于需求理解的冲突：产品优先
            ("product", "ui", "requirement"): "product",
            
            # 测试和开发关于Bug修复的冲突：测试优先
            ("tester", "backend", "bug_fix"): "tester",
            ("tester", "frontend", "bug_fix"): "tester",
            
            # 默认：老k仲裁
            ("*", "*", "*"): "lao_k"
        }
    
    def arbitrate(self, agent_a, agent_b, topic, message_a, message_b):
        # 查找优先级规则
        rule_key = (agent_a, agent_b, topic)
        priority_agent = self.priority_rules.get(rule_key, 
                      self.priority_rules.get(("*", "*", "*"), "lao_k"))
        
        if priority_agent == "lao_k":
            # 需要老k人工仲裁
            return self.escalate_to_lao_k(agent_a, agent_b, topic, message_a, message_b)
        else:
            # 按优先级决定
            return {
                "winner": priority_agent,
                "reason": f"按规则，{priority_agent}在此话题上优先",
                "action": "implement_winner_decision"
            }
```

---

## 五、OpenCode 实现方案

### 5.1 Agent 配置更新

```json
{
  "agent": {
    "backend": {
      "permission": {
        "edit": { "src/**": "allow", "*": "ask" },
        "bash": { "npm *": "allow", "npx prisma *": "allow", "*": "ask" },
        "read": "allow",
        "task": "deny",
        "webfetch": "allow",
        "mesh_write": {
          "mesh_communications/api_contracts": "allow",
          "mesh_communications/code_reviews": "allow"
        },
        "mesh_read": {
          "mesh_communications/api_contracts": "allow",
          "mesh_communications/code_reviews": "allow"
        }
      }
    },
    "frontend": {
      "permission": {
        "edit": { "src/**": "allow", "*": "ask" },
        "bash": { "npm *": "allow", "yarn *": "allow", "*": "ask" },
        "read": "allow",
        "task": "deny",
        "webfetch": "allow",
        "mesh_write": {
          "mesh_communications/api_contracts": "allow",
          "mesh_communications/code_reviews": "allow",
          "mesh_communications/design_specs": "allow"
        },
        "mesh_read": {
          "mesh_communications/api_contracts": "allow",
          "mesh_communications/code_reviews": "allow",
          "mesh_communications/design_specs": "allow"
        }
      }
    },
    "tester": {
      "permission": {
        "edit": { "**/*.test.*": "allow", "*": "deny" },
        "bash": { "npm test": "allow", "*": "ask" },
        "read": "allow",
        "task": "deny",
        "mesh_write": {
          "mesh_communications/code_reviews": "allow"
        },
        "mesh_read": {
          "mesh_communications/code_reviews": "allow"
        }
      }
    },
    "ui": {
      "permission": {
        "edit": { "*.md": "allow", "*": "deny" },
        "bash": "deny",
        "read": "allow",
        "task": "deny",
        "mesh_write": {
          "mesh_communications/design_specs": "allow",
          "mesh_communications/requirements": "allow"
        },
        "mesh_read": {
          "mesh_communications/design_specs": "allow",
          "mesh_communications/requirements": "allow"
        }
      }
    }
  }
}
```

### 5.2 RAG 工具封装

```python
# mesh_tools.py - Agent可用的RAG通讯工具

def mesh_write(collection, data):
    """写入Mesh通讯消息"""
    message = {
        "id": generate_id(),
        "trace_id": get_current_trace_id(),
        "created_at": datetime.utcnow().isoformat(),
        "status": "sent",
        **data
    }
    
    # 写入RAG
    rag_client.collection(collection).add(
        ids=[message["id"]],
        documents=[json.dumps(message)],
        metadatas=[{"from_agent": data["from_agent"], "to_agent": data["to_agent"]}]
    )
    
    # 通知老k（通过返回消息）
    return f"MESH_MSG:{message['id']}:{collection}"


def mesh_read(collection, message_id):
    """读取Mesh通讯消息"""
    result = rag_client.collection(collection).get(ids=[message_id])
    if result and result["documents"]:
        return json.loads(result["documents"][0])
    return None


def mesh_respond(collection, message_id, response_data):
    """响应Mesh通讯消息"""
    existing = mesh_read(collection, message_id)
    if not existing:
        return None
    
    existing["response"] = response_data
    existing["status"] = "responded"
    existing["responded_at"] = datetime.utcnow().isoformat()
    
    # 更新RAG
    rag_client.collection(collection).update(
        ids=[message_id],
        documents=[json.dumps(existing)]
    )
    
    return f"MESH_RESP:{message_id}:{collection}"
```

### 5.3 老k 的监控脚本

```python
# mesh_monitor.py - 老k的Mesh监控器

class MeshMonitor:
    def __init__(self):
        self.check_interval = 30  # 每30秒检查一次
        self.timeout_threshold = 300  # 5分钟超时
    
    def check_pending_messages(self):
        """检查未响应的消息"""
        pending = rag_client.collection("mesh_communications/messages").get(
            where={"status": "sent"}
        )
        
        alerts = []
        for msg in pending["metadatas"]:
            created_at = datetime.fromisoformat(msg["created_at"])
            if (datetime.utcnow() - created_at).seconds > self.timeout_threshold:
                alerts.append({
                    "type": "timeout",
                    "message_id": msg["id"],
                    "from_agent": msg["from_agent"],
                    "to_agent": msg["to_agent"],
                    "elapsed": (datetime.utcnow() - created_at).seconds
                })
        
        return alerts
    
    def check_conflicts(self):
        """检查写入冲突"""
        # 检查同一产物是否被多个Agent同时修改
        recent_writes = rag_client.collection("mesh_communications").get(
            where={"status": "sent"},
            limit=100
        )
        
        conflicts = []
        artifact_writes = {}
        for write in recent_writes["metadatas"]:
            artifact_id = write.get("artifact_ref", {}).get("id")
            if artifact_id:
                if artifact_id in artifact_writes:
                    conflicts.append({
                        "type": "conflict",
                        "artifact_id": artifact_id,
                        "agents": [artifact_writes[artifact_id]["from_agent"], write["from_agent"]]
                    })
                else:
                    artifact_writes[artifact_id] = write
        
        return conflicts
    
    def check_loops(self):
        """检查通讯死循环"""
        recent_messages = rag_client.collection("mesh_communications/messages").get(
            limit=50
        )
        
        loops = []
        agent_pairs = {}
        for msg in recent_messages["metadatas"]:
            pair = (msg["from_agent"], msg["to_agent"])
            if pair in agent_pairs:
                agent_pairs[pair] += 1
                if agent_pairs[pair] > 5:
                    loops.append({
                        "type": "loop",
                        "agents": pair,
                        "count": agent_pairs[pair]
                    })
            else:
                agent_pairs[pair] = 1
        
        return loops
    
    def run_check(self):
        """执行一次完整检查"""
        alerts = []
        alerts.extend(self.check_pending_messages())
        alerts.extend(self.check_conflicts())
        alerts.extend(self.check_loops())
        
        if alerts:
            # 通知老k处理
            self.notify_lao_k(alerts)
        
        return alerts
```

---

## 六、场景走查：Local Mesh 实际效果

### 场景 1：代码审查+修复（Mesh优化后）

```
时间线：
T+0s   BackendAgent完成代码，写入RAG，通知老k
T+1s   老k收到通知，立即调用TesterAgent
T+2s   TesterAgent从RAG读取代码
T+32s  TesterAgent完成审查，写入RAG，通知老k
T+33s  老k收到审查结果，发现有问题，调用BackendAgent
T+34s  BackendAgent从RAG读取审查反馈
T+64s  BackendAgent修复完成，写入RAG，通知老k
T+65s  老k调用TesterAgent回归验证
T+66s  TesterAgent从RAG读取修复后的代码
T+96s  TesterAgent确认通过，通知老k

总延迟：96秒
对比严格Hub-Spoke：120秒
节省：24秒（20%）
```

### 场景 2：UI↔前端协商（Mesh优化后）

```
时间线：
T+0s   UIDesigner完成设计，写入RAG，通知老k
T+1s   老k调用FrontendAgent
T+2s   FrontendAgent从RAG读取设计，发现问题，写入问题到RAG，通知老k
T+3s   老k调用UIDesigner
T+4s   UIDesigner从RAG读取问题，写入回答到RAG，通知老k
T+5s   老k调用FrontendAgent
T+6s   FrontendAgent从RAG读取回答，继续实现，完成，通知老k

总延迟：6 × (Agent执行 + 老k调度) ≈ 120秒
对比严格Hub-Spoke：180秒
节省：60秒（33%）
```

---

## 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Agent绕过老k直接通讯 | 低 | 高 | RAG权限严格控制，老k监控所有写入 |
| RAG成为性能瓶颈 | 中 | 中 | 使用高效向量DB，热点数据缓存 |
| 状态不一致 | 中 | 高 | 版本控制，冲突检测，老k仲裁 |
| 审计日志不完整 | 低 | 高 | 所有Mesh消息强制写入审计日志 |
| Agent忽略Mesh消息 | 中 | 中 | 超时检测，自动重试，老k兜底 |

---

## 八、总结

**Local Mesh 不是打破 Hub-Spoke，而是增强它。**

```
核心原则（不变）：
✅ 老k 是唯一的决策者
✅ 所有通讯可审计
✅ 老k 可随时干预
✅ 子Agent不可直接通讯

增强点（新增）：
✅ 通过 RAG 实现高效状态共享
✅ 减少不必要的中转延迟
✅ 保留完整的通讯记录
✅ 老k 监控并仲裁冲突
```

**延迟优化效果：**
- 代码审查场景：减少 20%
- UI↔前端协商：减少 33%
- API契约迭代：减少 25%
- 整体平均：减少 25-30%

**适用条件：**
- 仅限强依赖的Agent对
- 必须通过RAG通讯
- 必须通知老k
- 必须遵循标准协议

---

*Local Mesh 是 Hub-Spoke 的演进，不是替代。*
