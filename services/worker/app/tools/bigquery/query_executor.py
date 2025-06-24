"""BigQuery查询执行工具

该工具专门用于执行BigQuery SQL查询，为LangGraph工作流提供数据查询功能。
基于Thrasio IQ企业级多Agent系统的BigQuery x Looker数据分析Agent需求开发。
"""

import os
from typing import Dict, Any, List, Optional, Union, Annotated, Type
import pandas as pd
import structlog
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict


class QueryExecutorInput(BaseModel):
    """查询执行工具的输入参数"""

    table_name: str = Field(description="要查询的表名")
    query: str = Field(description="要执行的SQL查询语句")
    max_results: Optional[int] = Field(default=1000, description="最大返回结果数量")
    timeout: Optional[float] = Field(default=300.0, description="查询超时时间（秒）")
    dry_run: bool = Field(default=False, description="是否为试运行（不实际执行查询）")


class QueryResult(BaseModel):
    """查询结果模型"""

    success: bool = Field(description="查询是否成功")
    table_name: str = Field(description="查询的表名")
    row_count: int = Field(description="返回的行数")
    columns: List[str] = Field(description="列名列表")
    data: List[Dict[str, Any]] = Field(description="查询结果数据")
    bytes_processed: Optional[int] = Field(description="处理的字节数")
    execution_time: Optional[float] = Field(description="执行时间（秒）")
    error_message: Optional[str] = Field(description="错误信息（如果有）")


class BigQueryQueryExecutor(BaseTool):
    """
    BigQuery查询执行工具

    该工具用于执行指定表的SQL查询，获取查询结果。
    专为LangGraph工作流设计，支持数据分析Agent的查询执行功能。

    主要功能：
    1. 执行自定义SQL查询
    2. 支持查询参数化
    3. 返回结构化的查询结果
    4. 提供查询性能统计
    5. 完整的错误处理和权限检查
    6. 支持试运行模式
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "bigquery_query_executor"
    description: str = (
        "执行BigQuery SQL查询。"
        "输入表名和SQL查询语句，返回查询结果。"
        "支持结果数量限制、超时设置和试运行模式。适用于数据查询和分析。"
    )

    args_schema: Type[BaseModel] = QueryExecutorInput

    # 明确定义logger字段
    logger: Any = Field(default=None, exclude=True)
    project_id: Optional[str] = Field(default=None, exclude=True)
    client: Any = Field(default=None, exclude=True)

    def __init__(self, project_id: Optional[str] = None, **kwargs):
        """
        初始化查询执行工具

        Args:
            project_id: Google Cloud项目ID，如果不提供则从环境变量获取
            **kwargs: 其他参数传递给BaseTool
        """
        super().__init__(**kwargs)
        self.logger = structlog.get_logger()
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")

        if not self.project_id:
            raise ValueError("项目ID必须提供或设置GOOGLE_CLOUD_PROJECT环境变量")

        # 初始化BigQuery客户端
        try:
            self.client = bigquery.Client(project=self.project_id)
            self.logger.info(
                "BigQuery查询执行工具初始化成功", project_id=self.project_id
            )
        except Exception as e:
            self.logger.error("BigQuery客户端初始化失败", error=str(e))
            raise

    def _run(
        self,
        table_name: str,
        query: str,
        max_results: int = 1000,
        timeout: float = 300.0,
        dry_run: bool = False,
    ) -> str:
        """
        执行BigQuery查询

        Args:
            table_name: 要查询的表名
            query: SQL查询语句
            max_results: 最大返回结果数量
            timeout: 查询超时时间（秒）
            dry_run: 是否为试运行

        Returns:
            JSON格式的查询结果字符串
        """
        import time
        import json

        start_time = time.time()

        try:
            self.logger.info(
                "开始执行BigQuery查询",
                table_name=table_name,
                query_length=len(query),
                max_results=max_results,
                dry_run=dry_run,
            )

            # 配置查询作业
            job_config = bigquery.QueryJobConfig()
            job_config.dry_run = dry_run

            # 执行查询
            query_job = self.client.query(query, job_config=job_config, timeout=timeout)

            # 如果是试运行，返回估算信息
            if dry_run:
                execution_time = time.time() - start_time
                result = QueryResult(
                    success=True,
                    table_name=table_name,
                    row_count=0,
                    columns=[],
                    data=[],
                    bytes_processed=query_job.total_bytes_processed,
                    execution_time=execution_time,
                    error_message=None,
                )

                self.logger.info(
                    "试运行完成",
                    table_name=table_name,
                    bytes_processed=query_job.total_bytes_processed,
                    execution_time=execution_time,
                )

                return json.dumps(result.dict(), ensure_ascii=False, indent=2)

            # 等待查询完成并获取结果
            results = query_job.result(timeout=timeout)

            # 转换为DataFrame并限制结果数量
            df = results.to_dataframe()
            
            # 如果需要限制结果数量，在DataFrame级别进行截取
            if max_results and len(df) > max_results:
                df = df.head(max_results)

            execution_time = time.time() - start_time

            # 处理日期时间类型以确保JSON序列化兼容性
            df_serializable = df.copy()
            for col in df_serializable.columns:
                if df_serializable[col].dtype == 'object':
                    # 检查是否包含日期时间对象
                    sample_val = df_serializable[col].dropna().iloc[0] if not df_serializable[col].dropna().empty else None
                    if sample_val is not None and hasattr(sample_val, 'isoformat'):
                        df_serializable[col] = df_serializable[col].astype(str)
                elif 'datetime' in str(df_serializable[col].dtype) or 'date' in str(df_serializable[col].dtype):
                    df_serializable[col] = df_serializable[col].astype(str)

            # 构建结果
            result = QueryResult(
                success=True,
                table_name=table_name,
                row_count=len(df),
                columns=df.columns.tolist(),
                data=df_serializable.to_dict("records"),
                bytes_processed=query_job.total_bytes_processed,
                execution_time=execution_time,
                error_message=None,
            )

            self.logger.info(
                "查询执行成功",
                table_name=table_name,
                row_count=len(df),
                bytes_processed=query_job.total_bytes_processed,
                execution_time=execution_time,
            )

            return json.dumps(result.dict(), ensure_ascii=False, indent=2)

        except NotFound as e:
            error_msg = f"表或数据集未找到: {str(e)}"
            self.logger.error(
                "查询失败 - 资源未找到", table_name=table_name, error=error_msg
            )

        except Forbidden as e:
            error_msg = f"权限不足: {str(e)}"
            self.logger.error(
                "查询失败 - 权限不足", table_name=table_name, error=error_msg
            )

        except GoogleCloudError as e:
            error_msg = f"BigQuery错误: {str(e)}"
            self.logger.error(
                "查询失败 - BigQuery错误", table_name=table_name, error=error_msg
            )

        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            self.logger.error(
                "查询失败 - 未知错误", table_name=table_name, error=error_msg
            )

        # 返回错误结果
        execution_time = time.time() - start_time
        error_result = QueryResult(
            success=False,
            table_name=table_name,
            row_count=0,
            columns=[],
            data=[],
            bytes_processed=None,
            execution_time=execution_time,
            error_message=error_msg,
        )

        return json.dumps(error_result.dict(), ensure_ascii=False, indent=2)

    async def _arun(
        self,
        table_name: str,
        query: str,
        max_results: int = 1000,
        timeout: float = 300.0,
        dry_run: bool = False,
    ) -> str:
        """
        异步执行BigQuery查询

        Args:
            table_name: 要查询的表名
            query: SQL查询语句
            max_results: 最大返回结果数量
            timeout: 查询超时时间（秒）
            dry_run: 是否为试运行

        Returns:
            JSON格式的查询结果字符串
        """
        # 对于BigQuery，我们使用同步方法，因为google-cloud-bigquery库主要是同步的
        return self._run(table_name, query, max_results, timeout, dry_run)

    def validate_query(self, query: str, table_name: str) -> bool:
        """
        验证查询语句的基本安全性

        Args:
            query: SQL查询语句
            table_name: 表名

        Returns:
            是否通过验证
        """
        # 基本的安全检查
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "INSERT",
            "UPDATE",
            "CREATE",
            "ALTER",
            "GRANT",
            "REVOKE",
        ]

        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                self.logger.warning(
                    "查询包含危险关键字", table_name=table_name, keyword=keyword
                )
                return False

        return True


# 创建工具实例的便捷函数
def create_query_executor(project_id: Optional[str] = None) -> BigQueryQueryExecutor:
    """
    创建BigQuery查询执行工具实例

    Args:
        project_id: Google Cloud项目ID

    Returns:
        BigQueryQueryExecutor实例
    """
    return BigQueryQueryExecutor(project_id=project_id)
