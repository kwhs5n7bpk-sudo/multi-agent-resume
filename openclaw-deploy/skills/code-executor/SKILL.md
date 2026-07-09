---
name: code-executor
description: 安全执行代码和Shell命令
metadata:
  {
    "openclaw":
      {
        "requires": { "bins": ["python3"] }
      }
  }
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

### 使用方法
```bash
python3 {baseDir}/engine/code_executor.py python "print('Hello')"
python3 {baseDir}/engine/code_executor.py node "console.log('Hello')"
```
