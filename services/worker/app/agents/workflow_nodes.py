"""数据分析代理的工作流节点实现"""

import json
from typing import Any, Dict

import pandas as pd
import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.state import AppState
from app.prompts.analysis_prompts import (
    ANALYSIS_REPORT_PROMPT,
    ERROR_ANALYSIS_PROMPT,
    INTENT_ANALYSIS_PROMPT,
    TASK_SAFETY_FILTER_PROMPT,
)

logger = structlog.get_logger()


class WorkflowNodes:
    """工作流节点实现的混入类"""

    def welcome_node(self, state: AppState) -> AppState:
        """欢迎节点 - 显示所有可用的数据集"""
        logger.info("执行欢迎节点")
        state["current_step"] = "welcome"

        try:
            # 获取所有数据集
            datasets = self.bq_client.list_datasets()
            state["available_datasets"] = datasets

            # 生成欢迎信息
            welcome_msg = "Welcome to the Intelligent Data Analysis System!\n\nAvailable datasets:\n"
            for i, dataset in enumerate(datasets, 1):
                welcome_msg += f"{i}. {dataset}\n"

            print(welcome_msg)
            logger.info("欢迎节点执行完成", datasets_count=len(datasets))

        except Exception as e:
            logger.error("获取数据集失败", error=str(e))
            state["error_message"] = f"无法连接到BigQuery或获取数据集: {str(e)}"

        return state

    def select_dataset_node(self, state: AppState) -> AppState:
        """数据集选择节点"""
        logger.info("执行数据集选择节点")
        state["current_step"] = "select_dataset"

        if state.get("error_message"):
            return state

        try:
            datasets = state["available_datasets"]

            # 命令行交互选择数据集
            while True:
                try:
                    choice = input("Please select a dataset number (enter a number): ").strip()
                    dataset_index = int(choice) - 1

                    if 0 <= dataset_index < len(datasets):
                        selected_dataset = datasets[dataset_index]
                        state["selected_dataset"] = selected_dataset
                        print(f"Selected dataset: {selected_dataset}")
                        logger.info("数据集选择完成", selected_dataset=selected_dataset)
                        break
                    else:
                        print("Invalid selection, please try again!")

                except ValueError:
                    print("Please enter a valid number!")
                except KeyboardInterrupt:
                    print("\nOperation cancelled by user")
                    state["error_message"] = "用户取消操作"
                    break

        except Exception as e:
            logger.error("数据集选择失败", error=str(e))
            state["error_message"] = f"数据集选择失败: {str(e)}"

        return state

    def show_tables_node(self, state: AppState) -> AppState:
        """显示表格节点"""
        logger.info("执行显示表格节点")
        state["current_step"] = "show_tables"

        if state.get("error_message"):
            return state

        try:
            dataset = state["selected_dataset"]
            tables = self.bq_client.list_tables(dataset)
            state["tables_in_dataset"] = tables

            # 显示表格信息
            print(f"\nTables in dataset '{dataset}':\n")
            if tables:
                for i, table in enumerate(tables, 1):
                    print(f"{i}. {table}")
            else:
                print("No tables in this dataset")
                state["error_message"] = (
                    f"数据集 '{dataset}' 中没有表格，请选择其他数据集"
                )
                return state

            logger.info("表格显示完成", dataset=dataset, tables_count=len(tables))

        except Exception as e:
            logger.error(
                "获取表格失败", error=str(e), dataset=state.get("selected_dataset")
            )
            state["error_message"] = f"无法获取数据集中的表格: {str(e)}"

        return state

    def get_user_task_node(self, state: AppState) -> AppState:
        """获取用户任务节点"""
        logger.info("执行获取用户任务节点")
        state["current_step"] = "get_user_task"

        if state.get("error_message"):
            return state
        try:
            print("\nPlease describe the data analysis task you want to perform:")
            print("(For example: analyze sales trends, view user behavior patterns, count order quantities, etc.)")

            user_task = input("Analysis task: ").strip()

            if not user_task:
                print("Task description cannot be empty, please try again!")
                return state  # 重新获取用户输入

            state["user_task"] = user_task
            state["retry_count"] = 0  # 重置重试计数

            # print(f"Analysis task recorded: {user_task}")
            logger.info("用户任务获取完成", user_task=user_task)

        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            state["error_message"] = "用户取消操作"
        except Exception as e:
            logger.error("获取用户任务失败", error=str(e))
            state["error_message"] = f"获取用户任务失败: {str(e)}"

        return state

    def filter_task_node(self, state: AppState) -> AppState:
        """任务安全过滤节点"""
        logger.info("执行任务安全过滤节点")
        state["current_step"] = "filter_task"

        if state.get("error_message"):
            return state

        try:
            user_task = state["user_task"]

            # 使用LLM进行安全过滤
            prompt = TASK_SAFETY_FILTER_PROMPT.format(user_task=user_task)
            response = self.llm.invoke([HumanMessage(content=prompt)])

            # 解析响应
            try:
                # 尝试从响应中提取JSON部分
                response_content = response.content.strip()
                logger.info("LLM原始响应", response=response_content)

                # 如果响应包含markdown代码块，提取JSON部分
                if "```json" in response_content:
                    start = response_content.find("```json") + 7
                    end = response_content.find("```", start)
                    if end != -1:
                        response_content = response_content[start:end].strip()
                elif "```" in response_content:
                    start = response_content.find("```") + 3
                    end = response_content.find("```", start)
                    if end != -1:
                        response_content = response_content[start:end].strip()

                filter_result = json.loads(response_content)

                if filter_result.get("is_safe", False):
                    state["filtered_task"] = filter_result.get(
                        "cleaned_task", user_task
                    )
                    print("✓ Task safety check passed")
                    logger.info(
                        "任务安全过滤通过",
                        filtered_task=filter_result.get("cleaned_task"),
                    )
                else:
                    print(
                        f"✗ Task safety check failed: {filter_result.get('reason', 'Unknown reason')}"
                    )
                    state["error_message"] = (
                        f"任务不安全: {filter_result.get('reason', '未知原因')}"
                    )
                    logger.warning(
                        "任务安全过滤失败", reason=filter_result.get("reason")
                    )

            except (json.JSONDecodeError, KeyError) as e:
                logger.error("LLM响应解析失败", response=response.content, error=str(e))
                state["error_message"] = "任务安全检查失败，请重新描述任务"

        except Exception as e:
            logger.error("任务安全过滤异常", error=str(e))
            state["error_message"] = f"任务安全检查异常: {str(e)}"

        return state

    def read_schemas_node(self, state: AppState) -> AppState:
        """读取表结构节点"""
        logger.info("执行读取表结构节点")
        state["current_step"] = "read_schemas"

        if state.get("error_message"):
            return state

        try:
            dataset = state["selected_dataset"]
            tables = state["tables_in_dataset"]

            if not tables:
                state["error_message"] = f"数据集 '{dataset}' 中没有表格，无法继续"
                return state

            schemas = {}

            print("Reading Table Schema...")

            for table in tables:
                try:
                    schema = self.bq_client.get_table_schema(dataset, table)
                    schemas[table] = schema
                    print(f"✓ Successfully read {table} schema")
                except Exception as e:
                    logger.warning("读取表结构失败", table=table, error=str(e))
                    schemas[table] = []

            state["table_schemas"] = schemas
            logger.info("表结构读取完成", dataset=dataset, tables_count=len(schemas))

        except Exception as e:
            logger.error("读取表结构异常", error=str(e))
            state["error_message"] = f"读取表结构失败: {str(e)}"

        return state
