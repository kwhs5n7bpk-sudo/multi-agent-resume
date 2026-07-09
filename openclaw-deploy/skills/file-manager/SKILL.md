---
name: file-manager
description: 文件读写管理
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"] }
      }
  }
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

### 使用方法
```bash
python3 {baseDir}/engine/file_manager.py read ./readme.md
python3 {baseDir}/engine/file_manager.py write ./output.txt "内容"
python3 {baseDir}/engine/file_manager.py list ./src
```
