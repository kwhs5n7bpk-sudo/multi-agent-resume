---
name: rag-search
description: 向量检索知识库，支持语义搜索和精确匹配
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"], "env": ["LLM_API_KEY"] }
      }
  }
---

## RAG Search

使用向量数据库进行语义检索。

### 使用方法
```bash
python3 {baseDir}/engine/rag_search.py search "collection_name" "查询内容"
```

### 支持的操作
- `search`: 语义搜索
- `write`: 写入文档
- `delete`: 删除文档

### 示例
```bash
# 语义搜索
python3 {baseDir}/engine/rag_search.py search docs "如何部署Docker"

# 写入文档
python3 {baseDir}/engine/rag_search.py write docs ./readme.md

# 删除文档
python3 {baseDir}/engine/rag_search.py delete docs doc_id_123
```
