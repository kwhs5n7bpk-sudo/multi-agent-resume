FROM node:20-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip3 install -r requirements.txt

# 安装OpenClaw
RUN npm install -g openclaw@latest

# 创建工作目录
RUN mkdir -p ~/.openclaw/workspace-lao-k \
    ~/.openclaw/workspace-product \
    ~/.openclaw/workspace-ui \
    ~/.openclaw/workspace-frontend \
    ~/.openclaw/workspace-backend \
    ~/.openclaw/workspace-tester \
    ~/.openclaw/workspace-ops

# 复制工作区文件
COPY workspaces/ ~/.openclaw/

# 复制技能文件
COPY skills/ ~/.openclaw/skills/

# 复制配置文件
COPY openclaw.json ~/.openclaw/

# 暴露端口
EXPOSE 8080 9090

# 启动命令
CMD ["openclaw", "start"]
