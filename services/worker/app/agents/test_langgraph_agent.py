#!/usr/bin/env python3
"""
一个用于测试LLM和Langsmith配置的简单LangGraph代理。

功能：
1. 连接到BigQuery。
2. 列出所有可用的数据集。
3. 使用LLM将数据集列表转换为Mermaid图表。
4. 打印Mermaid图表。
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, TypedDict

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

import structlog
from langgraph.graph import StateGraph, END

from langchain_google_vertexai import ChatVertexAI

from core.config import get_settings
from tools.bigquery.client import BigQueryClient


logger = structlog.get_logger(__name__)


class GraphState(TypedDict):
    """Graph state"""
    datasets: List[str]
    mermaid_diagram: str
    error: str | None


class TestLangGraphAgent:
    """一个简单的测试代理"""

    def __init__(self):
        self.settings = get_settings()
        # 使用BigQuery专用的项目ID
        self.bq_client = BigQueryClient(project_id=self.settings.google_cloud.bigquery_project_id)
        # 初始化LLM客户端
        llm_options = self.settings.get_llm_client_options()
        self.llm_client = ChatVertexAI(
            project=llm_options['project'],
            location=llm_options['location'],
            model_name="gemini-2.5-flash"
        )

    def list_datasets(self, state: GraphState) -> GraphState:
        """列出所有BigQuery数据集"""
        logger.info("正在列出BigQuery数据集...")
        try:
            datasets = self.bq_client.list_datasets()
            logger.info(f"找到 {len(datasets)} 个数据集")
            return {**state, "datasets": datasets}
        except Exception as e:
            logger.error("列出数据集时出错", error=str(e))
            return {**state, "error": "Failed to list BigQuery datasets."}

    def generate_mermaid_diagram(self, state: GraphState) -> GraphState:
        """使用LLM生成Mermaid图表"""
        logger.info("正在生成Mermaid图表...")
        datasets = state.get("datasets")
        if not datasets:
            return {**state, "error": "No datasets found to generate diagram."}

        prompt = f"""
        请为以下BigQuery数据集列表创建一个Mermaid流程图：

        {datasets}

        请确保输出是一个有效的Mermaid代码块。
        例如:
        ```mermaid
        graph TD;
            A[Dataset 1] --> B[Dataset 2];
            A --> C[Dataset 3];
        ```
        """

        try:
            response = self.llm_client.invoke(prompt)
            mermaid_code = response.content
            logger.info("成功生成Mermaid图表")
            return {**state, "mermaid_diagram": mermaid_code}
        except Exception as e:
            logger.error("生成Mermaid图表时出错", error=str(e))
            return {**state, "error": "Failed to generate Mermaid diagram."}

    def build_graph(self):
        """构建LangGraph工作流"""
        workflow = StateGraph(GraphState)

        workflow.add_node("list_datasets", self.list_datasets)
        workflow.add_node("generate_mermaid", self.generate_mermaid_diagram)

        workflow.set_entry_point("list_datasets")
        workflow.add_edge("list_datasets", "generate_mermaid")
        workflow.add_edge("generate_mermaid", END)

        return workflow.compile()

def main():
    """主执行函数"""
    # 确保已设置必要的环境变量（在.env文件中）
    # GCP_PROJECT_ID="thrasio-dev-ai-agent"  # 默认GCP项目
    # GCP_BIGQUERY_PROJECT_ID="thrasio-dev-data-wh-7ee095"  # BigQuery专用项目
    # LLM_PROJECT_ID="thrasio-dev-ai-agent"  # LLM项目
    # LANGSMITH_TRACING="true"  # 可选：启用Langsmith追踪
    # LANGSMITH_API_KEY="..."  # 可选：Langsmith API密钥
    # LANGSMITH_PROJECT="..."  # 可选：Langsmith项目名称
    # 使用Application Default Credentials (ADC) 进行认证

    logger.info("开始执行测试LangGraph代理...")

    agent = TestLangGraphAgent()
    graph = agent.build_graph()

    initial_state = {"datasets": [], "mermaid_diagram": "", "error": None}
    final_state = graph.invoke(initial_state)

    if final_state.get("error"):
        logger.error("代理执行失败", error=final_state["error"])
    else:
        logger.info("代理执行成功！")
        print("\n--- 生成的Mermaid图表 ---\n")
        print(final_state["mermaid_diagram"])
        print("\n--------------------------\n")

if __name__ == "__main__":
    main()