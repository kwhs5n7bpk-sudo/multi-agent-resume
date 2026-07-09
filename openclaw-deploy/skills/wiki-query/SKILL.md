---
name: wiki-query
description: 知识图谱查询，支持实体关系分析和推理
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"] }
      }
  }
---

## Wiki Query

使用知识图谱进行关系分析。

### 使用方法
```bash
python3 {baseDir}/engine/wiki_query.py query "查询内容"
```

### 支持的操作
- `query`: 查询实体关系
- `write`: 写入实体和关系
- `stats`: 获取统计信息

### 示例
```bash
# 查询实体关系
python3 {baseDir}/engine/wiki_query.py query "前端和后端的关系"

# 写入实体
python3 {baseDir}/engine/wiki_query.py write entity "React" '{"type": "framework"}'

# 获取统计信息
python3 {baseDir}/engine/wiki_query.py stats
```
