#!/bin/bash

# 设置项目根目录，以便Python可以找到模块
export PYTHONPATH=$(pwd)

# --- Google Cloud 配置 ---
echo "正在从gcloud获取项目ID..."
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

# --- 创建 .env 文件 ---
# 这是一种比export更可靠的传递环境变量给Pydantic的方式

# 先删除旧的.env文件以避免混淆
rm -f .env

echo "正在创建 .env 配置文件..."

cat > .env << EOL
# Langsmith (可选, 用于追踪)
# 取消下面的注释并填入您的API密钥
# LANGSMITH_TRACING="true"
# LANGSMITH_API_KEY="YOUR_LANGSMITH_API_KEY"
# LANGSMITH_PROJECT="Thrasio-IQ-Test"

# LLM Provider
LLM_PROVIDER="google"

# Google Cloud Project ID
EOL

if [ -z "$PROJECT_ID" ]; then
    echo "警告：无法通过gcloud获取项目ID。"
    echo "请手动编辑项目根目录下的 .env 文件并设置 GOOGLE_CLOUD_PROJECT_ID。"
    echo 'GOOGLE_CLOUD_PROJECT_ID="YOUR_GCP_PROJECT_ID_HERE"' >> .env
    # 即使失败也继续，让Pydantic在运行时报告更清晰的错误
else
    echo "成功获取项目ID: $PROJECT_ID"
    echo "GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}" >> .env
fi

# 运行测试代理
echo "\n正在运行测试代理..."
python3 services/worker/app/agents/test_langgraph_agent.py