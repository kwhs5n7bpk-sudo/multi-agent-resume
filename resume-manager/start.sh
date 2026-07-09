#!/bin/bash
echo "=== 启动简历管理后台 ==="

pip3 install -r requirements.txt 2>/dev/null

python3 app.py
