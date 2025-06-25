"""数据分析代理的工作流节点实现 - 第二部分"""

import json
from typing import Any, Dict, List

import pandas as pd
import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.state import AppState
from app.prompts.analysis_prompts import (
    ANALYSIS_REPORT_PROMPT,
    ERROR_ANALYSIS_PROMPT,
    INTENT_ANALYSIS_PROMPT,
)

logger = structlog.get_logger()


class WorkflowNodesPart2:
    """工作流节点实现的混入类 - 第二部分"""

    def generate_queries_node(self, state: AppState) -> AppState:
        """查询生成节点"""
        logger.info("执行查询生成节点")
        state["current_step"] = "generate_queries"

        if state.get("error_message"):
            return state

        try:
            user_task = state["filtered_task"]
            table_schemas = state["table_schemas"]

            # 构建表结构信息
            schema_info = self._format_schema_info(
                table_schemas, state["selected_dataset"]
            )

            # 使用LLM生成SQL查询
            prompt = INTENT_ANALYSIS_PROMPT.format(
                user_task=user_task, table_schemas=schema_info
            )

            # print("正在分析意图并生成查询...")
            response = self.llm.invoke([HumanMessage(content=prompt)])

            try:
                # 尝试从响应中提取JSON部分
                response_content = response.content.strip()
                logger.info("查询生成LLM原始响应", response=response_content)

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

                analysis_result = json.loads(response_content)

                # 提取生成的查询
                queries = []
                for query_info in analysis_result.get("sql_queries", []):
                    if isinstance(query_info, dict) and "sql" in query_info:
                        sql = query_info["sql"]
                        # 修复表名格式
                        fixed_sql = self._fix_table_names_in_query(
                            sql, state["selected_dataset"], state["tables_in_dataset"]
                        )
                        queries.append(fixed_sql)
                    elif isinstance(query_info, str):
                        # 修复表名格式
                        fixed_sql = self._fix_table_names_in_query(
                            query_info,
                            state["selected_dataset"],
                            state["tables_in_dataset"],
                        )
                        queries.append(fixed_sql)

                state["generated_queries"] = queries

                # print(f"✓ 已生成 {len(queries)} 个查询")
                # print(f"分析意图: {analysis_result.get('analysis_intent', '未提供')}")

                logger.info(
                    "查询生成完成",
                    queries_count=len(queries),
                    analysis_intent=analysis_result.get("analysis_intent"),
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(
                    "查询生成响应解析失败", response=response.content, error=str(e)
                )
                state["error_message"] = "查询生成失败，请重新描述任务"

        except Exception as e:
            logger.error("查询生成异常", error=str(e))
            state["error_message"] = f"查询生成失败: {str(e)}"

        return state

    def test_queries_node(self, state: AppState) -> AppState:
        """查询测试节点"""
        logger.info("执行查询测试节点")
        state["current_step"] = "test_queries"

        if state.get("error_message"):
            return state

        try:
            queries = state["generated_queries"]
            test_results = []

            # print("正在测试查询...")

            for i, query in enumerate(queries, 1):
                try:
                    # print(f"测试查询 {i}/{len(queries)}")

                    # 小规模测试 - 限制返回10条数据
                    test_query = self._add_limit_to_query(query, 10)

                    # 执行测试查询
                    df = self.bq_client.execute_query(
                        test_query, timeout=30, max_results=10
                    )

                    test_result = {
                        "query_index": i,
                        "original_query": query,
                        "test_query": test_query,
                        "success": True,
                        "row_count": len(df),
                        "columns": list(df.columns) if not df.empty else [],
                        "sample_data": (
                            df.head(3).to_dict("records") if not df.empty else []
                        ),
                    }

                    test_results.append(test_result)
                    # print(f"✓ 查询 {i} 测试成功 ({len(df)} 行)")

                except Exception as e:
                    test_result = {
                        "query_index": i,
                        "original_query": query,
                        "success": False,
                        "error": str(e),
                    }
                    test_results.append(test_result)
                    # print(f"✗ 查询 {i} 测试失败: {str(e)}")
                    # logger.warning("查询测试失败", query_index=i, error=str(e))

            state["test_results"] = test_results

            # 检查是否有成功的查询
            successful_tests = [r for r in test_results if r["success"]]
            if successful_tests:
                # print(f"测试完成: {len(successful_tests)}/{len(queries)} 个查询成功")
                logger.info(
                    "查询测试完成",
                    total_queries=len(queries),
                    successful_queries=len(successful_tests),
                )
            else:
                state["error_message"] = "所有查询测试都失败了"
                logger.error("所有查询测试都失败")

        except Exception as e:
            logger.error("查询测试异常", error=str(e))
            state["error_message"] = f"查询测试异常: {str(e)}"

        return state

    def execute_queries_node(self, state: AppState) -> AppState:
        """执行查询节点"""
        logger.info("执行查询执行节点")
        state["current_step"] = "execute_queries"

        if state.get("error_message"):
            return state

        try:
            test_results = state["test_results"]
            successful_queries = [r for r in test_results if r["success"]]

            if not successful_queries:
                state["error_message"] = "没有可执行的有效查询"
                return state

            query_results = []

            print("正在执行完整查询...")

            for test_result in successful_queries:
                try:
                    query = test_result["original_query"]
                    query_index = test_result["query_index"]

                    print(f"执行查询 {query_index}/{len(successful_queries)}")

                    # 执行完整查询
                    df = self.bq_client.execute_query(
                        query,
                        timeout=self.settings.google_cloud.bigquery_timeout,
                        max_results=self.settings.google_cloud.bigquery_max_results,
                    )

                    # 检查结果大小，如果太大则存储到外部记忆
                    result_size = len(str(df.to_dict("records")))
                    if result_size > 50000:  # 50KB阈值
                        # 存储大型结果到外部记忆
                        summary = f"查询 {query_index} 结果: {len(df)} 行 x {len(df.columns)} 列"
                        memory_key = self.memory.store_large_result(
                            self.session_id, df.to_dict("records"), summary
                        )

                        result_data = {
                            "query_index": query_index,
                            "query": query,
                            "row_count": len(df),
                            "column_count": len(df.columns),
                            "columns": list(df.columns),
                            "is_large_result": True,
                            "memory_key": memory_key,
                            "summary": summary,
                            "sample_data": df.head(5).to_dict("records"),
                        }

                        # 更新记忆键列表
                        if "memory_keys" not in state:
                            state["memory_keys"] = []
                        state["memory_keys"].append(memory_key)

                    else:
                        result_data = {
                            "query_index": query_index,
                            "query": query,
                            "row_count": len(df),
                            "column_count": len(df.columns),
                            "columns": list(df.columns),
                            "is_large_result": False,
                            "data": df.to_dict("records"),
                        }

                    query_results.append(result_data)
                    print(f"✓ 查询 {query_index} 执行成功 ({len(df)} 行)")

                except Exception as e:
                    logger.error(
                        "查询执行失败",
                        query_index=test_result["query_index"],
                        error=str(e),
                    )
                    # 继续执行其他查询
                    continue

            state["query_results"] = query_results

            if query_results:
                print(f"查询执行完成: {len(query_results)} 个查询成功")
                logger.info("查询执行完成", successful_queries=len(query_results))
            else:
                state["error_message"] = "所有查询执行都失败了"

        except Exception as e:
            logger.error("查询执行异常", error=str(e))
            state["error_message"] = f"查询执行异常: {str(e)}"

        return state

    def generate_report_node(self, state: AppState) -> AppState:
        """生成分析报告节点"""
        logger.info("执行生成分析报告节点")
        state["current_step"] = "generate_report"

        if state.get("error_message"):
            return state

        try:
            user_task = state["user_task"]
            query_results = state["query_results"]

            if not query_results:
                state["error_message"] = "没有查询结果可用于分析"
                return state

            # 准备结果数据用于报告生成
            results_summary = self._prepare_results_for_report(query_results)

            # 使用LLM生成分析报告
            prompt = ANALYSIS_REPORT_PROMPT.format(
                user_task=user_task, query_results=results_summary
            )

            print("Generating analysis report...")
            response = self.llm.invoke([HumanMessage(content=prompt)])

            analysis_report = response.content
            state["analysis_report"] = analysis_report

            # 显示分析报告
            print("\n" + "=" * 60)
            print("Intelligent Data Analysis Report")
            print("=" * 60)
            print(analysis_report)
            print("=" * 60)

            logger.info("分析报告生成完成", session_id=self.session_id)

        except Exception as e:
            logger.error("生成分析报告异常", error=str(e))
            state["error_message"] = f"生成分析报告失败: {str(e)}"

        return state

    def handle_error_node(self, state: AppState) -> AppState:
        """错误处理节点"""
        logger.info("执行错误处理节点")
        state["current_step"] = "handle_error"

        error_message = state.get("error_message", "未知错误")

        print(f"\n❌ 发生错误: {error_message}")
        print("分析工作流已终止")

        logger.error(
            "工作流错误处理", error_message=error_message, session_id=self.session_id
        )

        return state

    # 辅助方法
    def _format_schema_info(self, table_schemas: Dict[str, List], dataset: str) -> str:
        """格式化表结构信息"""
        schema_info = f"数据集: {dataset}\n"
        schema_info += (
            f"重要提醒: 在SQL查询中，表名必须使用完整格式 `{dataset}.table_name`\n\n"
        )

        for table_name, schema in table_schemas.items():
            schema_info += f"表名: {table_name}\n"
            schema_info += f"完整表名格式: {dataset}.{table_name}\n"
            schema_info += (
                f"SQL查询示例: SELECT * FROM `{dataset}.{table_name}` LIMIT 10\n"
            )
            schema_info += "字段:\n"

            for field in schema:
                schema_info += f"  - {field['name']} ({field['field_type']})"
                if field.get("description"):
                    schema_info += f": {field['description']}"
                schema_info += "\n"

            schema_info += "\n"

        return schema_info

    def _add_limit_to_query(self, query: str, limit: int) -> str:
        """为查询添加LIMIT子句"""
        query = query.strip()
        if query.upper().find("LIMIT") == -1:
            return f"{query} LIMIT {limit}"
        return query

    def _prepare_results_for_report(self, query_results: List[Dict]) -> str:
        """准备查询结果用于报告生成"""
        results_summary = ""

        for result in query_results:
            results_summary += f"\n查询 {result['query_index']}:\n"
            results_summary += (
                f"行数: {result['row_count']}, 列数: {result['column_count']}\n"
            )
            results_summary += f"列名: {', '.join(result['columns'])}\n"

            if result.get("is_large_result"):
                results_summary += f"结果概要: {result['summary']}\n"
                results_summary += "样本数据:\n"
                for row in result.get("sample_data", [])[:3]:
                    results_summary += f"  {row}\n"
            else:
                results_summary += "数据:\n"
                for row in result.get("data", [])[:5]:
                    results_summary += f"  {row}\n"
                if len(result.get("data", [])) > 5:
                    results_summary += f"  ... (共{len(result.get('data', []))}行)\n"

            results_summary += "\n"

        return results_summary

    def _fix_table_names_in_query(
        self, query: str, dataset: str, tables: List[str]
    ) -> str:
        """修复SQL查询中的表名格式，确保使用dataset.table格式"""
        fixed_query = query

        for table in tables:
            # 查找各种可能的表名格式
            patterns_to_replace = [
                f"FROM {table}",
                f"FROM `{table}`",
                f"from {table}",
                f"from `{table}`",
                f"JOIN {table}",
                f"JOIN `{table}`",
                f"join {table}",
                f"join `{table}`",
            ]

            # 替换为正确的格式
            correct_format = f"`{dataset}.{table}`"

            for pattern in patterns_to_replace:
                if pattern in fixed_query:
                    # 确保不是已经有dataset前缀的表名
                    if f"{dataset}." not in pattern:
                        replacement = pattern.replace(table, correct_format).replace(
                            f"`{correct_format}`", correct_format
                        )
                        fixed_query = fixed_query.replace(pattern, replacement)

        # 记录是否进行了修复
        if fixed_query != query:
            logger.info("修复了SQL查询中的表名格式", original=query, fixed=fixed_query)

        return fixed_query
