---
name: web-search
description: 网络搜索
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"] }
      }
  }
---

## Web Search

搜索互联网获取信息。

### 使用场景
- 查找技术文档
- 搜索API文档
- 获取最新信息

### 使用方法
```bash
python3 {baseDir}/engine/web_search.py "查询内容"
```

### 示例
```bash
# 搜索技术文档
python3 {baseDir}/engine/web_search.py "React 18 新特性"

# 搜索API文档
python3 {baseDir}/engine/web_search.py "OpenAI API 文档"
```
