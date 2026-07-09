#!/bin/bash
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
openclaw start

echo "=== 系统已启动 ==="
echo "Web界面: http://localhost:8080"
echo "监控面板: http://localhost:9090"
