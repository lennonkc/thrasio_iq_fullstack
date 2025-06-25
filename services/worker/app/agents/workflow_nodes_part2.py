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

            print("正在分析意图并生成查询...")
            response = self.llm.invoke([HumanMessage(content=prompt)])

            try:
                analysis_result = json.loads(response.content)

                # 提取生成的查询
                queries = []
                for query_info in analysis_result["sql_queries"]:
                    queries.append(query_info["sql"])

                state["generated_queries"] = queries

                print(f"✓ 已生成 {len(queries)} 个查询")
                print(f"分析意图: {analysis_result['analysis_intent']}")

                logger.info(
                    "查询生成完成",
                    queries_count=len(queries),
                    analysis_intent=analysis_result["analysis_intent"],
                )

            except json.JSONDecodeError:
                logger.error("查询生成响应解析失败", response=response.content)
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

            print("正在测试查询...")

            for i, query in enumerate(queries, 1):
                try:
                    print(f"测试查询 {i}/{len(queries)}")

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
                    print(f"✓ 查询 {i} 测试成功 ({len(df)} 行)")

                except Exception as e:
                    test_result = {
                        "query_index": i,
                        "original_query": query,
                        "success": False,
                        "error": str(e),
                    }
                    test_results.append(test_result)
                    print(f"✗ 查询 {i} 测试失败: {str(e)}")
                    logger.warning("查询测试失败", query_index=i, error=str(e))

            state["test_results"] = test_results

            # 检查是否有成功的查询
            successful_tests = [r for r in test_results if r["success"]]
            if successful_tests:
                print(f"测试完成: {len(successful_tests)}/{len(queries)} 个查询成功")
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

            print("正在生成分析报告...")
            response = self.llm.invoke([HumanMessage(content=prompt)])

            analysis_report = response.content
            state["analysis_report"] = analysis_report

            # 显示分析报告
            print("\\n" + "=" * 60)
            print("智能数据分析报告")
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

        print(f"\\n❌ 发生错误: {error_message}")
        print("分析工作流已终止")

        logger.error(
            "工作流错误处理", error_message=error_message, session_id=self.session_id
        )

        return state

    # 辅助方法
    def _format_schema_info(self, table_schemas: Dict[str, List], dataset: str) -> str:
        """格式化表结构信息"""
        schema_info = f"数据集: {dataset}\\n\\n"

        for table_name, schema in table_schemas.items():
            schema_info += f"表名: {table_name}\\n"
            schema_info += "字段:\\n"

            for field in schema:
                schema_info += f"  - {field['name']} ({field['field_type']})"
                if field.get("description"):
                    schema_info += f": {field['description']}"
                schema_info += "\\n"

            schema_info += "\\n"

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
            results_summary += f"\\n查询 {result['query_index']}:\\n"
            results_summary += (
                f"行数: {result['row_count']}, 列数: {result['column_count']}\\n"
            )
            results_summary += f"列名: {', '.join(result['columns'])}\\n"

            if result.get("is_large_result"):
                results_summary += f"结果概要: {result['summary']}\\n"
                results_summary += "样本数据:\\n"
                for row in result.get("sample_data", [])[:3]:
                    results_summary += f"  {row}\\n"
            else:
                results_summary += "数据:\\n"
                for row in result.get("data", [])[:5]:
                    results_summary += f"  {row}\\n"
                if len(result.get("data", [])) > 5:
                    results_summary += f"  ... (共{len(result.get('data', []))}行)\\n"

            results_summary += "\\n"

        return results_summary
