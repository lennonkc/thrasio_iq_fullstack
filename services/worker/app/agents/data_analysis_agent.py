"""数据分析代理 - 基于LangGraph的智能BigQuery数据分析工作流"""

import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import pandas as pd
import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, StateGraph

from app.agents.base_agent import BaseAgent
from app.agents.state import AppState
from app.agents.workflow_nodes import WorkflowNodes
from app.agents.workflow_nodes_part2 import WorkflowNodesPart2
from app.core.config import get_settings
from app.memory.external_memory import ExternalMemory
from app.prompts.analysis_prompts import (
    ANALYSIS_REPORT_PROMPT,
    ERROR_ANALYSIS_PROMPT,
    INTENT_ANALYSIS_PROMPT,
    TASK_SAFETY_FILTER_PROMPT,
)
from app.tools.bigquery.client import BigQueryClient

logger = structlog.get_logger()


class DataAnalysisAgent(BaseAgent, WorkflowNodes, WorkflowNodesPart2):
    """数据分析代理 - 智能分析BigQuery数据"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = get_settings()
        self.bq_client = BigQueryClient(
            project_id=self.settings.google_cloud.bigquery_project_id,
            credentials_path=self.settings.google_cloud.credentials_path,
        )
        self.llm = ChatVertexAI(
            model_name=self.settings.llm.model_name,
            temperature=self.settings.llm.temperature,
            project=self.settings.llm.project_id,
            location=self.settings.llm.vertex_ai_location,
        )
        self.memory = ExternalMemory()
        self.session_id = uuid.uuid4().hex[:8]
        logger.info("数据分析代理初始化完成", session_id=self.session_id)

    def create_workflow(self) -> StateGraph:
        """创建LangGraph工作流"""
        workflow = StateGraph(AppState)

        # 添加工作流节点
        workflow.add_node("welcome", self.welcome_node)
        workflow.add_node("select_dataset", self.select_dataset_node)
        workflow.add_node("show_tables", self.show_tables_node)
        workflow.add_node("get_user_task", self.get_user_task_node)
        workflow.add_node("filter_task", self.filter_task_node)
        workflow.add_node("read_schemas", self.read_schemas_node)
        workflow.add_node("generate_queries", self.generate_queries_node)
        workflow.add_node("test_queries", self.test_queries_node)
        workflow.add_node("execute_queries", self.execute_queries_node)
        workflow.add_node("generate_report", self.generate_report_node)
        workflow.add_node("handle_error", self.handle_error_node)

        # 设置起始节点
        workflow.set_entry_point("welcome")

        # 定义节点间的转换逻辑
        workflow.add_edge("welcome", "select_dataset")
        workflow.add_edge("select_dataset", "show_tables")

        # 条件边：表显示结果（处理空数据集）
        workflow.add_conditional_edges(
            "show_tables",
            self.should_continue_after_show_tables,
            {
                "continue": "get_user_task",
                "retry_dataset": "select_dataset",
                "error": "handle_error",
            },
        )

        workflow.add_edge("get_user_task", "filter_task")

        # 条件边：任务过滤结果
        workflow.add_conditional_edges(
            "filter_task",
            self.should_continue_after_filter,
            {
                "continue": "read_schemas",
                "retry": "get_user_task",
                "error": "handle_error",
            },
        )

        workflow.add_edge("read_schemas", "generate_queries")

        # 条件边：查询生成结果
        workflow.add_conditional_edges(
            "generate_queries",
            self.should_continue_after_generation,
            {"test": "test_queries", "retry": "get_user_task", "error": "handle_error"},
        )

        # 条件边：查询测试结果
        workflow.add_conditional_edges(
            "test_queries",
            self.should_continue_after_test,
            {
                "execute": "execute_queries",
                "retry": "generate_queries",
                "error": "handle_error",
            },
        )

        workflow.add_edge("execute_queries", "generate_report")
        workflow.add_edge("generate_report", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    async def run(self, **kwargs) -> Dict[str, Any]:
        """运行数据分析代理"""
        try:
            # 初始化状态
            initial_state = AppState(
                project_id=self.settings.google_cloud.bigquery_project_id,
                available_datasets=[],
                selected_dataset=None,
                tables_in_dataset=[],
                table_schemas=None,
                user_task=None,
                filtered_task=None,
                generated_queries=None,
                test_results=None,
                query_results=None,
                analysis_report=None,
                error_message=None,
                retry_count=0,
                messages=[],
                current_step="welcome",
                memory_keys=[],
            )

            # 创建并运行工作流
            workflow = self.create_workflow()
            final_state = await workflow.ainvoke(initial_state)

            return {
                "success": True,
                "session_id": self.session_id,
                "final_state": final_state,
                "analysis_report": final_state.get("analysis_report"),
                "error_message": final_state.get("error_message"),
            }

        except Exception as e:
            logger.error(
                "数据分析代理运行失败", error=str(e), session_id=self.session_id
            )
            return {"success": False, "session_id": self.session_id, "error": str(e)}

    async def astream(self, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """流式运行数据分析代理"""
        try:
            # 初始化状态
            initial_state = AppState(
                project_id=self.settings.google_cloud.bigquery_project_id,
                available_datasets=[],
                selected_dataset=None,
                tables_in_dataset=[],
                table_schemas=None,
                user_task=None,
                filtered_task=None,
                generated_queries=None,
                test_results=None,
                query_results=None,
                analysis_report=None,
                error_message=None,
                retry_count=0,
                messages=[],
                current_step="welcome",
                memory_keys=[],
            )

            # 创建并流式运行工作流
            workflow = self.create_workflow()
            async for state in workflow.astream(initial_state):
                yield {
                    "session_id": self.session_id,
                    "current_step": state.get("current_step", "unknown"),
                    "state_update": state,
                }

        except Exception as e:
            logger.error(
                "数据分析代理流式运行失败", error=str(e), session_id=self.session_id
            )
            yield {"session_id": self.session_id, "error": str(e)}

    # 条件判断方法
    def should_continue_after_filter(self, state: AppState) -> str:
        """过滤后的条件判断"""
        error_message = state.get("error_message")
        filtered_task = state.get("filtered_task")

        logger.info(
            "安全过滤条件判断",
            error_message=error_message,
            filtered_task=filtered_task,
            has_error=bool(error_message),
        )

        if error_message:
            if "不安全" in error_message:
                print("⚠️ Task is unsafe, returning for re-input")
                return "retry"  # 重新获取用户任务
            print("❌ Other error occurred, entering error handling")
            return "error"

        if filtered_task:
            print("✅ Safety check passed, continuing to next step")
            return "continue"
        else:
            print("⚠️ Filtered task is empty, please re-input")
            state["error_message"] = "过滤后的任务为空"
            return "retry"

    def should_continue_after_generation(self, state: AppState) -> str:
        """查询生成后的条件判断"""
        if state.get("error_message"):
            return "retry"
        if not state.get("generated_queries"):
            return "retry"
        return "test"

    def should_continue_after_test(self, state: AppState) -> str:
        """查询测试后的条件判断"""
        if state.get("error_message"):
            return "error"

        test_results = state.get("test_results", [])
        successful_tests = [r for r in test_results if r.get("success")]

        if not successful_tests:
            # 增加重试计数
            state["retry_count"] = state.get("retry_count", 0) + 1
            if state["retry_count"] < 3:
                return "retry"  # 重新生成查询
            else:
                state["error_message"] = "查询生成多次失败，无法继续"
                return "error"

        return "execute"

    def should_continue_after_show_tables(self, state: AppState) -> str:
        """显示表格后的条件判断"""
        error_message = state.get("error_message")
        tables = state.get("tables_in_dataset", [])

        logger.info(
            "表格显示条件判断",
            error_message=error_message,
            tables_count=len(tables),
            has_error=bool(error_message),
        )

        if error_message:
            if "没有表格" in error_message:
                print("⚠️ 数据集为空，请重新选择数据集")
                # 清除错误信息，允许重试
                state["error_message"] = None
                return "retry_dataset"
            return "error"

        if tables:
            return "continue"
        else:
            state["error_message"] = "数据集中没有表格"
            return "retry_dataset"
