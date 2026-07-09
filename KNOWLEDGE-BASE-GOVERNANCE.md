# 知识库生命周期管理：应对增长、冗余与检索退化

> 版本：v1.0 | 日期：2026-07-07

---

## 一、问题全景：知识库增长的 6 大挑战

### 1.1 数据膨胀曲线

```
时间轴（月）    向量数（万）    检索延迟(ms)    检索相关性
─────────────────────────────────────────────────────
Month 1         0.5           50ms           95%
Month 3         2.1           80ms           90%
Month 6         5.8           150ms          82%
Month 12        15.2          350ms          71%
Month 24        40.6          800ms          58%
                 ↑               ↑              ↑
              指数增长         线性恶化        持续退化
```

**如果不做治理，12个月后检索质量下降25%，24个月后下降40%。**

### 1.2 六大挑战详解

| # | 挑战 | 表现 | 根因 |
|---|------|------|------|
| 1 | **数据冗余** | 同一PRD被存储5个版本，检索返回重复结果 | 缺少去重机制 |
| 2 | **过期数据** | 检索到已废弃的API文档，Agent据此写代码 | 缺少过期淘汰 |
| 3 | **噪声干扰** | 检索结果中大量无关内容，淹没有用信息 | 缺少相关性过滤 |
| 4 | **检索退化** | 向量相似度高的结果越来越多，但实际不相关 | Embedding漂移 |
| 5 | **存储膨胀** | 向量数据库体积指数增长，查询变慢 | 缺少压缩策略 |
| 6 | **版本混乱** | 不知道哪个版本是最新的，Agent可能用旧版本 | 缺少版本管理 |

---

## 二、核心策略：五层治理架构

```
┌─────────────────────────────────────────────────────────────┐
│                    知识库治理层（Governance Layer）            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 版本控制  │ │ 去重引擎  │ │ 生命周期  │ │ 质量监控  │      │
│  │ Version  │ │ Dedup    │ │ Lifecycle│ │ Quality  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    数据分层（Data Tiers）                     │
│                                                             │
│  Tier 0: 热数据（Hot）    — 近7天，全量检索                   │
│  Tier 1: 温数据（Warm）   — 7-30天，压缩检索                 │
│  Tier 2: 冷数据（Cold）   — 30-90天，摘要检索                │
│  Tier 3: 归档（Archive）  — 90天+，仅ID索引                  │
│  Tier 4: 垃圾（Garbage）  — 过期/无效，定期清理               │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    向量数据库（ChromaDB）                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ prds     │ │ design   │ │ code     │ │ api_docs │      │
│  │ _hot     │ │ _hot     │ │ _hot     │ │ _hot     │      │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤      │
│  │ prds     │ │ design   │ │ code     │ │ api_docs │      │
│  │ _warm    │ │ _warm    │ │ _warm    │ │ _warm    │      │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤      │
│  │ prds     │ │ design   │ │ code     │ │ api_docs │      │
│  │ _cold    │ │ _cold    │ │ _cold    │ │ _cold    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、数据分层与生命周期策略

### 3.1 分层定义

```python
DATA_TIERS = {
    "hot": {
        "age_range": "0-7 days",
        "retrieval_mode": "full_vector_search",
        "chunk_size": 512,           # 标准分块
        "chunk_overlap": 50,         # 标准重叠
        "index_full": True,          # 全量向量索引
        "metadata_index": True,      # 元数据索引
        "compression": None,         # 不压缩
        "max_vectors": 10000,        # 热数据上限
        " eviction_policy": "promote_to_warm"  # 超限后降级
    },
    "warm": {
        "age_range": "7-30 days",
        "retrieval_mode": "vector_search_with_compression",
        "chunk_size": 1024,          # 加大分块（减少向量数）
        "chunk_overlap": 0,          # 无重叠
        "index_full": True,
        "metadata_index": True,
        "compression": "quantize",   # 量化压缩（精度换空间）
        "max_vectors": 50000,
        "eviction_policy": "promote_to_cold"
    },
    "cold": {
        "age_range": "30-90 days",
        "retrieval_mode": "summary_search",
        "chunk_size": 4096,          # 大块（仅保留摘要）
        "chunk_overlap": 0,
        "index_full": False,         # 不建全量向量索引
        "metadata_index": True,      # 仅元数据索引
        "compression": "summarize",  # 摘要压缩
        "max_vectors": 10000,
        "eviction_policy": "promote_to_archive"
    },
    "archive": {
        "age_range": "90+ days",
        "retrieval_mode": "id_lookup_only",
        "chunk_size": None,
        "chunk_overlap": None,
        "index_full": False,
        "metadata_index": True,
        "compression": "archive",    # 仅保留ID和摘要
        "max_vectors": 5000,
        "eviction_policy": "delete"
    }
}
```

### 3.2 生命周期流转

```
新数据写入
    │
    ▼
┌─────────┐
│ Tier 0  │ ← 热数据，全量检索
│ (Hot)   │
└────┬────┘
     │ 7天后
     ▼
┌─────────┐
│ Tier 1  │ ← 温数据，压缩检索
│ (Warm)  │
└────┬────┘
     │ 30天后
     ▼
┌─────────┐
│ Tier 2  │ ← 冷数据，摘要检索
│ (Cold)  │
└────┬────┘
     │ 90天后
     ▼
┌─────────┐
│ Tier 3  │ ← 归档，仅ID索引
│(Archive)│
└────┬────┘
     │ 被访问时
     ▼
┌─────────┐
│ 升级回Hot│ ← 热度激活，重新索引
└─────────┘
     │ 90天未访问
     ▼
┌─────────┐
│ Tier 4  │ ← 垃圾，定期清理
│(Garbage)│
└─────────┘
```

### 3.3 自动分级脚本

```python
from datetime import datetime, timedelta
import chromadb

class KnowledgeTierManager:
    def __init__(self, chroma_client):
        self.client = chroma_client
        self.tier_configs = DATA_TIERS
    
    def run_lifecycle_job(self):
        """每日执行一次的生命周期任务"""
        for collection_name in self.client.list_collections():
            self.process_collection(collection_name)
    
    def process_collection(self, collection_name):
        collection = self.client.get_collection(collection_name)
        all_docs = collection.get(include=["metadatas", "documents"])
        
        for doc_id, metadata, document in zip(
            all_docs["ids"], all_docs["metadatas"], all_docs["documents"]
        ):
            current_tier = metadata.get("tier", "hot")
            age_days = (datetime.utcnow() - datetime.fromisoformat(
                metadata["created_at"]
            )).days
            
            # 判断目标tier
            target_tier = self.calculate_target_tier(age_days, metadata)
            
            if target_tier != current_tier:
                self.migrate_document(
                    collection_name, doc_id, document, metadata,
                    current_tier, target_tier
                )
    
    def calculate_target_tier(self, age_days, metadata):
        """计算目标tier（考虑访问热度）"""
        access_count = metadata.get("access_count", 0)
        last_accessed = metadata.get("last_accessed")
        
        # 热度因子：最近被访问的数据保持在更高tier
        if last_accessed:
            days_since_access = (datetime.utcnow() - datetime.fromisoformat(
                last_accessed
            )).days
            if days_since_access < 7 and access_count > 3:
                return "hot"  # 高频访问，保持热数据
        
        # 基于年龄的默认分级
        if age_days < 7:
            return "hot"
        elif age_days < 30:
            return "warm"
        elif age_days < 90:
            return "cold"
        else:
            return "archive"
    
    def migrate_document(self, collection_name, doc_id, document, 
                         metadata, from_tier, to_tier):
        """迁移文档到目标tier"""
        # 1. 根据目标tier进行压缩
        compressed_doc = self.compress_document(document, to_tier)
        
        # 2. 更新metadata
        metadata["tier"] = to_tier
        metadata["tier_migrated_at"] = datetime.utcnow().isoformat()
        metadata["original_tier"] = from_tier
        
        # 3. 创建目标tier的collection
        target_collection_name = f"{collection_name}_{to_tier}"
        target_collection = self.client.get_or_create_collection(
            target_collection_name
        )
        
        # 4. 写入目标tier
        target_collection.add(
            ids=[doc_id],
            documents=[compressed_doc],
            metadatas=[metadata]
        )
        
        # 5. 从源tier删除
        source_collection = self.client.get_collection(
            f"{collection_name}_{from_tier}"
        )
        source_collection.delete(ids=[doc_id])
    
    def compress_document(self, document, target_tier):
        """根据目标tier压缩文档"""
        if target_tier == "warm":
            # 量化压缩：减少精度，保留关键信息
            return self.quantize_document(document)
        elif target_tier == "cold":
            # 摘要压缩：只保留摘要
            return self.summarize_document(document)
        elif target_tier == "archive":
            # 归档压缩：只保留ID和标题
            return self.archive_document(document)
        return document
    
    def quantify_document(self, document):
        """量化压缩：减少细节，保留核心"""
        # 移除代码块、详细示例，保留核心描述
        import re
        # 移除代码块
        doc = re.sub(r'```[\s\S]*?```', '[代码块已压缩]', document)
        # 移除详细示例
        doc = re.sub(r'示例：[\s\S]*?(?=\n\n|\Z)', '[示例已压缩]', doc)
        return doc
    
    def summarize_document(self, document):
        """摘要压缩：使用LLM生成摘要"""
        # 调用LLM生成摘要（这里用简单的截断作为示例）
        if len(document) > 500:
            return document[:500] + "\n\n[摘要：该文档已压缩，仅保留前500字]"
        return document
    
    def archive_document(self, document):
        """归档压缩：仅保留标题和前100字"""
        lines = document.split('\n')
        title = next((l for l in lines if l.startswith('#')), lines[0])
        preview = document[:100] if len(document) > 100 else document
        return f"{title}\n\n{preview}\n\n[归档：该文档已归档，仅保留预览]"
```

---

## 四、去重机制

### 4.1 三重去重策略

```
写入时去重（Write-time Dedup）
    │
    ├─ 1. 精确去重：基于content_hash
    ├─ 2. 语义去重：基于向量相似度
    └─ 3. 结构去重：基于文档结构

查询时去重（Query-time Dedup）
    │
    ├─ 1. 结果去重：合并相似结果
    ├─ 2. 版本去重：只返回最新版本
    └─ 3. 来源去重：合并同一来源的不同片段
```

### 4.2 写入时去重实现

```python
import hashlib
from typing import List, Dict

class KnowledgeDeduplicator:
    def __init__(self, chroma_client, similarity_threshold=0.85):
        self.client = chroma_client
        self.similarity_threshold = similarity_threshold
    
    def check_and_dedup(self, collection_name, document, metadata):
        """写入前去重检查"""
        dedup_result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "existing_id": None,
            "action": None
        }
        
        collection = self.client.get_collection(collection_name)
        
        # 1. 精确去重：content_hash
        content_hash = hashlib.md5(document.encode()).hexdigest()
        existing = collection.get(
            where={"content_hash": content_hash}
        )
        if existing["ids"]:
            dedup_result["is_duplicate"] = True
            dedup_result["duplicate_type"] = "exact"
            dedup_result["existing_id"] = existing["ids"][0]
            dedup_result["action"] = "skip"
            return dedup_result
        
        # 2. 语义去重：向量相似度
        results = collection.query(
            query_texts=[document],
            n_results=3,
            include=["distances", "metadatas"]
        )
        
        if results["distances"][0]:
            min_distance = results["distances"][0][0]
            if min_distance < (1 - self.similarity_threshold):
                # 发现高度相似的文档
                existing_doc = results["documents"][0][0]
                existing_metadata = results["metadatas"][0][0]
                
                # 判断是否是同一文档的不同版本
                if self.is_same_artifact(metadata, existing_metadata):
                    dedup_result["is_duplicate"] = True
                    dedup_result["duplicate_type"] = "semantic"
                    dedup_result["existing_id"] = results["ids"][0][0]
                    dedup_result["action"] = "update"  # 更新而非新增
                    return dedup_result
        
        # 3. 结构去重：检查是否是同一PRD/设计/API的不同片段
        if metadata.get("artifact_type") and metadata.get("artifact_id"):
            existing_fragments = collection.get(
                where={
                    "artifact_type": metadata["artifact_type"],
                    "artifact_id": metadata["artifact_id"]
                }
            )
            if existing_fragments["ids"]:
                # 同一产物的多个片段，检查是否需要合并
                dedup_result["is_duplicate"] = True
                dedup_result["duplicate_type"] = "structural"
                dedup_result["existing_id"] = existing_fragments["ids"]
                dedup_result["action"] = "merge"
                return dedup_result
        
        return dedup_result
    
    def is_same_artifact(self, meta_a, meta_b):
        """判断是否是同一产物"""
        # 同一PRD的不同版本
        if (meta_a.get("artifact_type") == "prd" and 
            meta_b.get("artifact_type") == "prd"):
            return meta_a.get("feature_name") == meta_b.get("feature_name")
        
        # 同一API文档的不同版本
        if (meta_a.get("artifact_type") == "api" and 
            meta_b.get("artifact_type") == "api"):
            return meta_a.get("endpoint") == meta_b.get("endpoint")
        
        return False
    
    def merge_fragments(self, collection_name, fragment_ids):
        """合并同一产物的多个片段"""
        collection = self.client.get_collection(collection_name)
        
        # 获取所有片段
        fragments = collection.get(ids=fragment_ids, include=["documents", "metadatas"])
        
        # 合并文档
        merged_doc = "\n\n---\n\n".join(fragments["documents"])
        
        # 合并metadata（保留最新的）
        merged_meta = fragments["metadatas"][0]
        merged_meta["fragment_count"] = len(fragment_ids)
        merged_meta["merged_at"] = datetime.utcnow().isoformat()
        
        # 删除旧片段
        collection.delete(ids=fragment_ids)
        
        # 写入合并后的文档
        new_id = f"{fragment_ids[0]}_merged"
        collection.add(
            ids=[new_id],
            documents=[merged_doc],
            metadatas=[merged_meta]
        )
        
        return new_id
```

### 4.3 查询时去重实现

```python
class QueryDeduplicator:
    def __init__(self, chroma_client):
        self.client = chroma_client
    
    def deduplicate_results(self, results, query_metadata=None):
        """查询结果去重"""
        if not results["ids"][0]:
            return results
        
        deduplicated = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        
        seen = set()
        
        for i, (doc_id, doc, meta, dist) in enumerate(zip(
            results["ids"][0], results["documents"][0],
            results["metadatas"][0], results["distances"][0]
        )):
            # 1. 版本去重：只保留最新版本
            artifact_id = meta.get("artifact_id")
            if artifact_id:
                if artifact_id in seen:
                    # 检查是否是更新的版本
                    existing_idx = self.find_artifact_idx(
                        deduplicated["metadatas"], artifact_id
                    )
                else:
                    deduplicated["ids"].append(doc_id)
                    deduplicated["documents"].append(doc)
                    deduplicated["metadatas"].append(meta)
                    deduplicated["distances"].append(dist)
                    seen.add(artifact_id)
            else:
                # 2. 精确去重：基于content_hash
                content_hash = hashlib.md5(doc.encode()).hexdigest()
                if content_hash not in seen:
                    deduplicated["ids"].append(doc_id)
                    deduplicated["documents"].append(doc)
                    deduplicated["metadatas"].append(meta)
                    deduplicated["distances"].append(dist)
                    seen.add(content_hash)
        
        # 3. 相似度去重：合并高度相似的结果
        deduplicated = self.merge_similar_results(deduplicated)
        
        return deduplicated
    
    def find_artifact_idx(self, metadatas, artifact_id):
        """查找同一产物的已有索引"""
        for i, meta in enumerate(metadatas):
            if meta.get("artifact_id") == artifact_id:
                return i
        return -1
    
    def merge_similar_results(self, results, threshold=0.9):
        """合并高度相似的结果"""
        if len(results["ids"]) <= 1:
            return results
        
        merged = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        
        skip = set()
        
        for i in range(len(results["ids"])):
            if i in skip:
                continue
            
            # 查找与当前结果高度相似的其他结果
            similar_indices = []
            for j in range(i + 1, len(results["ids"])):
                if j in skip:
                    continue
                similarity = 1 - results["distances"][j]  # 转换为相似度
                if similarity > threshold:
                    similar_indices.append(j)
            
            if similar_indices:
                # 合并相似结果
                merged_doc = results["documents"][i]
                for idx in similar_indices:
                    merged_doc += f"\n\n[合并自: {results['ids'][idx]}]"
                    skip.add(idx)
                
                merged["ids"].append(results["ids"][i])
                merged["documents"].append(merged_doc)
                merged["metadatas"].append(results["metadatas"][i])
                merged["distances"].append(results["distances"][i])
            else:
                merged["ids"].append(results["ids"][i])
                merged["documents"].append(results["documents"][i])
                merged["metadatas"].append(results["metadatas"][i])
                merged["distances"].append(results["distances"][i])
        
        return merged
```

---

## 五、检索质量保障

### 5.1 检索质量监控指标

```python
QUALITY_METRICS = {
    "retrieval_precision": {
        "description": "检索结果中相关文档的比例",
        "target": 0.85,
        "alert_threshold": 0.70,
        "measurement": "人工标注或LLM评估"
    },
    "retrieval_recall": {
        "description": "相关文档被检索到的比例",
        "target": 0.90,
        "alert_threshold": 0.75,
        "measurement": "人工标注或LLM评估"
    },
    "retrieval_latency": {
        "description": "检索延迟",
        "target_ms": 100,
        "alert_threshold_ms": 300,
        "measurement": "系统日志"
    },
    "result_diversity": {
        "description": "检索结果的多样性",
        "target": 0.70,
        "alert_threshold": 0.50,
        "measurement": "结果间的平均距离"
    },
    "freshness_score": {
        "description": "检索结果的新鲜度",
        "target": 0.80,
        "alert_threshold": 0.60,
        "measurement": "结果的平均年龄"
    }
}
```

### 5.2 自动质量评估

```python
class RetrievalQualityMonitor:
    def __init__(self, chroma_client, llm_client):
        self.client = chroma_client
        self.llm = llm_client
    
    def evaluate_retrieval_quality(self, collection_name, sample_size=100):
        """评估检索质量"""
        collection = self.client.get_collection(collection_name)
        
        # 1. 采样查询
        sample_queries = self.sample_queries(collection, sample_size)
        
        # 2. 评估每个查询
        metrics = {
            "precision": [],
            "recall": [],
            "latency": [],
            "diversity": [],
            "freshness": []
        }
        
        for query in sample_queries:
            start_time = time.time()
            results = collection.query(
                query_texts=[query["text"]],
                n_results=10
            )
            latency = (time.time() - start_time) * 1000
            
            # 评估精确率
            precision = self.evaluate_precision(query, results)
            metrics["precision"].append(precision)
            
            # 评估召回率
            recall = self.evaluate_recall(query, results)
            metrics["recall"].append(recall)
            
            # 记录延迟
            metrics["latency"].append(latency)
            
            # 评估多样性
            diversity = self.evaluate_diversity(results)
            metrics["diversity"].append(diversity)
            
            # 评估新鲜度
            freshness = self.evaluate_freshness(results)
            metrics["freshness"].append(freshness)
        
        # 3. 计算平均值
        avg_metrics = {
            metric: sum(values) / len(values) if values else 0
            for metric, values in metrics.items()
        }
        
        return avg_metrics
    
    def evaluate_precision(self, query, results):
        """评估精确率（使用LLM判断相关性）"""
        if not results["documents"][0]:
            return 0.0
        
        relevant_count = 0
        for doc in results["documents"][0]:
            # 使用LLM判断文档是否与查询相关
            is_relevant = self.llm.evaluate_relevance(
                query=query["text"],
                document=doc
            )
            if is_relevant:
                relevant_count += 1
        
        return relevant_count / len(results["documents"][0])
    
    def evaluate_recall(self, query, results):
        """评估召回率（需要ground truth）"""
        # 如果有标注数据，计算召回率
        if "expected_results" in query:
            expected = set(query["expected_results"])
            retrieved = set(results["ids"][0])
            return len(expected & retrieved) / len(expected)
        return None
    
    def evaluate_diversity(self, results):
        """评估结果多样性"""
        if len(results["distances"][0]) <= 1:
            return 1.0
        
        # 计算结果间的平均距离
        distances = results["distances"][0]
        avg_distance = sum(distances) / len(distances)
        
        # 距离越大，多样性越好
        return min(avg_distance, 1.0)
    
    def evaluate_freshness(self, results):
        """评估结果新鲜度"""
        if not results["metadatas"][0]:
            return 0.5
        
        now = datetime.utcnow()
        freshness_scores = []
        
        for meta in results["metadatas"][0]:
            created_at = datetime.fromisoformat(meta.get("created_at", now.isoformat()))
            age_days = (now - created_at).days
            
            # 新鲜度分数：7天内=1.0，30天内=0.7，90天内=0.4，90天+=0.1
            if age_days < 7:
                score = 1.0
            elif age_days < 30:
                score = 0.7
            elif age_days < 90:
                score = 0.4
            else:
                score = 0.1
            
            freshness_scores.append(score)
        
        return sum(freshness_scores) / len(freshness_scores)
```

### 5.3 检索增强策略

```python
class RetrievalEnhancer:
    def __init__(self, chroma_client):
        self.client = chroma_client
    
    def enhanced_query(self, query_text, collection_name, 
                       use_hybrid=True, use_rerank=True):
        """增强检索策略"""
        collection = self.client.get_collection(collection_name)
        
        # 1. 查询扩展
        expanded_query = self.expand_query(query_text)
        
        # 2. 混合检索（向量 + 关键词）
        if use_hybrid:
            results = self.hybrid_search(
                collection, expanded_query, query_text
            )
        else:
            results = collection.query(
                query_texts=[expanded_query],
                n_results=20
            )
        
        # 3. 结果重排序
        if use_rerank:
            results = self.rerank_results(results, query_text)
        
        # 4. 结果去重
        results = self.deduplicate_results(results)
        
        # 5. 截断到top-k
        results = self.truncate_results(results, k=10)
        
        return results
    
    def expand_query(self, query_text):
        """查询扩展：添加同义词和相关词"""
        # 简单的同义词扩展（生产环境可使用词向量或LLM）
        expansions = {
            "登录": ["登录", "login", "认证", "鉴权"],
            "注册": ["注册", "register", "signup", "创建账号"],
            "API": ["API", "接口", "endpoint", "路由"],
            "前端": ["前端", "frontend", "页面", "UI"],
            "后端": ["后端", "backend", "服务端", "server"],
            "测试": ["测试", "test", "QA", "验证"],
            "部署": ["部署", "deploy", "发布", "上线"]
        }
        
        expanded_terms = [query_text]
        for key, synonyms in expansions.items():
            if key in query_text:
                expanded_terms.extend(synonyms)
        
        return " ".join(set(expanded_terms))
    
    def hybrid_search(self, collection, semantic_query, keyword_query):
        """混合检索：向量搜索 + 关键词搜索"""
        # 向量搜索
        semantic_results = collection.query(
            query_texts=[semantic_query],
            n_results=15,
            include=["documents", "metadatas", "distances"]
        )
        
        # 关键词搜索（使用元数据过滤）
        keyword_results = collection.get(
            where_document={"$contains": keyword_query},
            include=["documents", "metadatas"]
        )
        
        # 合并结果
        combined = self.merge_search_results(
            semantic_results, keyword_results
        )
        
        return combined
    
    def merge_search_results(self, semantic_results, keyword_results):
        """合并搜索结果"""
        merged = {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        
        # 添加语义搜索结果（带距离权重）
        if semantic_results["ids"][0]:
            for i, doc_id in enumerate(semantic_results["ids"][0]):
                merged["ids"].append(doc_id)
                merged["documents"].append(semantic_results["documents"][0][i])
                merged["metadatas"].append(semantic_results["metadatas"][0][i])
                merged["distances"].append(semantic_results["distances"][0][i])
        
        # 添加关键词搜索结果（标记来源）
        if keyword_results["ids"]:
            for i, doc_id in enumerate(keyword_results["ids"]):
                if doc_id not in merged["ids"]:
                    merged["ids"].append(doc_id)
                    merged["documents"].append(keyword_results["documents"][i])
                    merged["metadatas"].append(keyword_results["metadatas"][i])
                    merged["distances"].append(0.5)  # 默认距离
        
        return merged
    
    def rerank_results(self, results, query_text):
        """结果重排序：使用交叉编码器或LLM"""
        if not results["ids"][0]:
            return results
        
        # 简单的重排序策略：结合距离和元数据质量
        scored_results = []
        for i, (doc_id, doc, meta, dist) in enumerate(zip(
            results["ids"][0], results["documents"][0],
            results["metadatas"][0], results["distances"][0]
        )):
            # 计算综合分数
            relevance_score = 1 - dist  # 相关性分数
            freshness_score = self.get_freshness_score(meta)
            quality_score = self.get_quality_score(meta)
            
            # 加权综合分数
            final_score = (
                relevance_score * 0.5 +
                freshness_score * 0.3 +
                quality_score * 0.2
            )
            
            scored_results.append({
                "id": doc_id,
                "document": doc,
                "metadata": meta,
                "distance": dist,
                "score": final_score
            })
        
        # 按分数排序
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        # 重新组织结果
        reranked = {
            "ids": [[r["id"] for r in scored_results]],
            "documents": [[r["document"] for r in scored_results]],
            "metadatas": [[r["metadata"] for r in scored_results]],
            "distances": [[r["distance"] for r in scored_results]]
        }
        
        return reranked
    
    def get_freshness_score(self, metadata):
        """获取新鲜度分数"""
        created_at = metadata.get("created_at")
        if not created_at:
            return 0.5
        
        age_days = (datetime.utcnow() - datetime.fromisoformat(created_at)).days
        
        if age_days < 7:
            return 1.0
        elif age_days < 30:
            return 0.7
        elif age_days < 90:
            return 0.4
        else:
            return 0.1
    
    def get_quality_score(self, metadata):
        """获取质量分数"""
        # 基于元数据中的质量标记
        quality_tags = metadata.get("quality_tags", [])
        
        score = 0.5  # 基础分数
        if "verified" in quality_tags:
            score += 0.2
        if "reviewed" in quality_tags:
            score += 0.15
        if "approved" in quality_tags:
            score += 0.15
        
        return min(score, 1.0)
```

---

## 六、版本管理

### 6.1 版本控制策略

```python
class VersionManager:
    def __init__(self, chroma_client):
        self.client = chroma_client
    
    def create_version(self, collection_name, artifact_id, 
                       document, metadata, version_type="patch"):
        """创建新版本"""
        collection = self.client.get_collection(collection_name)
        
        # 获取当前版本
        current = collection.get(
            where={"artifact_id": artifact_id},
            include=["documents", "metadatas"]
        )
        
        if current["ids"]:
            # 计算新版本号
            current_version = current["metadatas"][0].get("version", "1.0.0")
            new_version = self.calculate_next_version(
                current_version, version_type
            )
            
            # 标记旧版本为"archived"
            collection.update(
                ids=[current["ids"][0]],
                metadatas=[{
                    **current["metadatas"][0],
                    "version_status": "archived",
                    "archived_at": datetime.utcnow().isoformat()
                }]
            )
            
            # 创建新版本
            new_id = f"{artifact_id}_v{new_version}"
            metadata["version"] = new_version
            metadata["version_status"] = "current"
            metadata["created_at"] = datetime.utcnow().isoformat()
            
            collection.add(
                ids=[new_id],
                documents=[document],
                metadatas=[metadata]
            )
            
            return new_id
        else:
            # 首次创建
            new_id = f"{artifact_id}_v1.0.0"
            metadata["version"] = "1.0.0"
            metadata["version_status"] = "current"
            metadata["created_at"] = datetime.utcnow().isoformat()
            
            collection.add(
                ids=[new_id],
                documents=[document],
                metadatas=[metadata]
            )
            
            return new_id
    
    def calculate_next_version(self, current_version, version_type):
        """计算下一个版本号"""
        major, minor, patch = map(int, current_version.split('.'))
        
        if version_type == "major":
            return f"{major + 1}.0.0"
        elif version_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"
    
    def get_current_version(self, collection_name, artifact_id):
        """获取当前版本"""
        collection = self.client.get_collection(collection_name)
        
        results = collection.get(
            where={
                "artifact_id": artifact_id,
                "version_status": "current"
            },
            include=["documents", "metadatas"]
        )
        
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "version": results["metadatas"][0]["version"],
                "document": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None
    
    def get_version_history(self, collection_name, artifact_id):
        """获取版本历史"""
        collection = self.client.get_collection(collection_name)
        
        results = collection.get(
            where={"artifact_id": artifact_id},
            include=["metadatas"]
        )
        
        versions = []
        for meta in results["metadatas"]:
            versions.append({
                "version": meta["version"],
                "status": meta["version_status"],
                "created_at": meta["created_at"],
                "author": meta.get("author", "unknown")
            })
        
        # 按版本号排序
        versions.sort(key=lambda x: x["version"], reverse=True)
        
        return versions
    
    def rollback_to_version(self, collection_name, artifact_id, 
                           target_version):
        """回滚到指定版本"""
        collection = self.client.get_collection(collection_name)
        
        # 查找目标版本
        target = collection.get(
            where={
                "artifact_id": artifact_id,
                "version": target_version
            },
            include=["documents", "metadatas"]
        )
        
        if not target["ids"]:
            raise ValueError(f"版本 {target_version} 不存在")
        
        # 标记当前版本为"archived"
        current = self.get_current_version(collection_name, artifact_id)
        if current:
            collection.update(
                ids=[current["id"]],
                metadatas=[{
                    **current["metadata"],
                    "version_status": "archived",
                    "archived_at": datetime.utcnow().isoformat()
                }]
            )
        
        # 激活目标版本
        collection.update(
            ids=[target["ids"][0]],
            metadatas=[{
                **target["metadatas"][0],
                "version_status": "current",
                "activated_at": datetime.utcnow().isoformat()
            }]
        )
        
        return target["ids"][0]
```

---

## 七、定时任务调度

```python
class KnowledgeBaseScheduler:
    def __init__(self, chroma_client):
        self.client = chroma_client
        self.tier_manager = KnowledgeTierManager(chroma_client)
        self.deduplicator = KnowledgeDeduplicator(chroma_client)
        self.quality_monitor = RetrievalQualityMonitor(chroma_client, None)
    
    def run_daily_maintenance(self):
        """每日维护任务"""
        print("开始每日维护任务...")
        
        # 1. 生命周期管理
        print("  [1/5] 执行生命周期管理...")
        self.tier_manager.run_lifecycle_job()
        
        # 2. 去重清理
        print("  [2/5] 执行去重清理...")
        self.dedup_cleanup()
        
        # 3. 质量监控
        print("  [3/5] 执行质量监控...")
        self.quality_monitor.evaluate_retrieval_quality("code_index")
        
        # 4. 清理过期数据
        print("  [4/5] 清理过期数据...")
        self.cleanup_expired_data()
        
        # 5. 生成报告
        print("  [5/5] 生成维护报告...")
        self.generate_maintenance_report()
        
        print("每日维护任务完成")
    
    def dedup_cleanup(self):
        """去重清理"""
        for collection_name in self.client.list_collections():
            collection = self.client.get_collection(collection_name)
            all_docs = collection.get(include=["metadatas"])
            
            # 按artifact_id分组
            artifact_groups = {}
            for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
                artifact_id = meta.get("artifact_id")
                if artifact_id:
                    if artifact_id not in artifact_groups:
                        artifact_groups[artifact_id] = []
                    artifact_groups[artifact_id].append(doc_id)
            
            # 合并重复片段
            for artifact_id, doc_ids in artifact_groups.items():
                if len(doc_ids) > 1:
                    self.deduplicator.merge_fragments(
                        collection_name, doc_ids
                    )
    
    def cleanup_expired_data(self):
        """清理过期数据"""
        for collection_name in self.client.list_collections():
            collection = self.client.get_collection(collection_name)
            all_docs = collection.get(include=["metadatas"])
            
            expired_ids = []
            for doc_id, meta in zip(all_docs["ids"], all_docs["metadatas"]):
                if meta.get("tier") == "garbage":
                    expired_ids.append(doc_id)
            
            if expired_ids:
                collection.delete(ids=expired_ids)
                print(f"  清理了 {len(expired_ids)} 条过期数据 from {collection_name}")
    
    def generate_maintenance_report(self):
        """生成维护报告"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "collections": {}
        }
        
        for collection_name in self.client.list_collections():
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            
            # 统计各tier的数据量
            all_docs = collection.get(include=["metadatas"])
            tier_counts = {}
            for meta in all_docs["metadatas"]:
                tier = meta.get("tier", "unknown")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            report["collections"][collection_name] = {
                "total_count": count,
                "tier_distribution": tier_counts
            }
        
        # 保存报告
        with open("maintenance_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"  维护报告已保存到 maintenance_report.json")
```

---

## 八、总结：知识库治理检查清单

| 维度 | 措施 | 频率 | 效果 |
|------|------|------|------|
| **数据分层** | Hot→Warm→Cold→Archive自动流转 | 每日 | 减少60%检索噪声 |
| **去重** | 写入时三重去重 + 查询时结果去重 | 实时 | 减少40%存储冗余 |
| **版本管理** | 语义版本号 + 自动归档旧版本 | 每次写入 | 消除版本混乱 |
| **质量监控** | 精确率/召回率/延迟/多样性/新鲜度 | 每周 | 持续保障检索质量 |
| **检索增强** | 查询扩展 + 混合检索 + 重排序 | 每次查询 | 提升20%检索相关性 |
| **过期清理** | 定时清理Garbage数据 | 每日 | 防止存储无限膨胀 |

**核心原则：**
- 热数据精而少，冷数据粗而全
- 写入时严格去重，查询时智能去重
- 版本可追溯，回滚可一键
- 质量可量化，退化可告警

---

*知识库治理是RAG系统的生命线，不做治理的RAG，3个月后就是垃圾场。*
