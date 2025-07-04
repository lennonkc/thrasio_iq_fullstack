#!/usr/bin/env python3
"""
BigQuery数据集探索工具

该工具专门用于探索BigQuery数据集中的表结构，为LangGraph工作流提供数据集和表的发现功能。
基于Thrasio IQ企业级多Agent系统的BigQuery x Looker数据分析Agent需求开发。
"""

import os
from typing import Dict, Any, List, Optional, Tuple, Type
from datetime import datetime
import structlog
from google.cloud.exceptions import NotFound, Forbidden, GoogleCloudError
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .client import BigQueryClient


class DatasetExplorerInput(BaseModel):
    """数据集探索工具的输入参数"""
    dataset_id: str = Field(description="要探索的数据集ID")
    include_table_details: bool = Field(default=False, description="是否包含表的详细信息（如列信息、行数等）")
    table_pattern: Optional[str] = Field(default=None, description="表名过滤模式（支持通配符）")
    max_tables: int = Field(default=100, description="最大返回表数量")


class TableInfo(BaseModel):
    """表信息模型"""
    table_id: str = Field(description="表ID")
    table_type: str = Field(description="表类型（TABLE, VIEW, EXTERNAL等）")
    created: Optional[datetime] = Field(description="创建时间")
    modified: Optional[datetime] = Field(description="最后修改时间")
    num_rows: Optional[int] = Field(description="行数")
    num_bytes: Optional[int] = Field(description="存储大小（字节）")
    description: Optional[str] = Field(description="表描述")
    schema_fields: Optional[List[Dict[str, Any]]] = Field(description="表结构字段信息")


class DatasetInfo(BaseModel):
    """数据集信息模型"""
    dataset_id: str = Field(description="数据集ID")
    project_id: str = Field(description="项目ID")
    location: str = Field(description="数据集位置")
    created: Optional[datetime] = Field(description="创建时间")
    modified: Optional[datetime] = Field(description="最后修改时间")
    description: Optional[str] = Field(description="数据集描述")
    table_count: int = Field(description="表数量")
    tables: List[TableInfo] = Field(description="表列表")


class BigQueryDatasetExplorer(BaseTool):
    """
    BigQuery数据集探索工具
    
    该工具用于探索指定数据集中的所有表，获取表的基本信息和结构。
    专为LangGraph工作流设计，支持数据分析Agent的Schema发现和查询规划功能。
    
    主要功能：
    1. 列出数据集中的所有表
    2. 获取表的基本元数据（创建时间、行数、大小等）
    3. 可选获取表的详细结构信息
    4. 支持表名过滤和数量限制
    5. 提供完整的错误处理和权限检查
    """
    
    name: str = "bigquery_dataset_explorer"
    description: str = (
        "探索BigQuery数据集中的表结构。"
        "输入数据集ID，返回该数据集中所有表的信息，包括表名、类型、行数、结构等。"
        "支持表名过滤和详细信息获取。适用于数据发现和查询规划。"
    )
    args_schema: Type[BaseModel] = DatasetExplorerInput
    
    def __init__(self, client: BigQueryClient, **kwargs):
        """
        初始化数据集探索工具
        
        Args:
            client: BigQueryClient实例
            **kwargs: 其他参数传递给BaseTool
        """
        super().__init__(**kwargs)
        self.client = client
        self.logger = structlog.get_logger()
        self.logger.info("BigQuery数据集探索工具初始化成功")
    
    def _run(
        self, 
        dataset_id: str,
        include_table_details: bool = False,
        table_pattern: Optional[str] = None,
        max_tables: int = 100
    ) -> Dict[str, Any]:
        """
        执行数据集探索
        
        Args:
            dataset_id: 数据集ID
            include_table_details: 是否包含表的详细信息
            table_pattern: 表名过滤模式
            max_tables: 最大返回表数量
            
        Returns:
            包含数据集和表信息的字典
        """
        try:
            self.logger.info(
                "开始探索数据集", 
                dataset_id=dataset_id, 
                include_details=include_table_details,
                pattern=table_pattern,
                max_tables=max_tables
            )
            
            # 获取数据集信息
            dataset_info = self._get_dataset_info(dataset_id)
            
            # 获取表列表
            tables = self._list_tables(
                dataset_id, 
                include_table_details, 
                table_pattern, 
                max_tables
            )
            
            # 构建完整的数据集信息
            result = {
                "success": True,
                "dataset_info": {
                    "dataset_id": dataset_info["dataset_id"],
                    "project_id": dataset_info["project_id"],
                    "location": dataset_info["location"],
                    "created": dataset_info["created"],
                    "modified": dataset_info["modified"],
                    "description": dataset_info["description"],
                    "table_count": len(tables)
                },
                "tables": tables,
                "metadata": {
                    "explored_at": datetime.now().isoformat(),
                    "include_details": include_table_details,
                    "table_pattern": table_pattern,
                    "max_tables": max_tables,
                    "actual_table_count": len(tables)
                }
            }
            
            self.logger.info(
                "数据集探索完成", 
                dataset_id=dataset_id, 
                table_count=len(tables)
            )
            
            return result
            
        except NotFound:
            error_msg = f"数据集 '{dataset_id}' 不存在"
            self.logger.warning("数据集不存在", dataset_id=dataset_id)
            return {
                "success": False,
                "error": error_msg,
                "error_type": "NOT_FOUND",
                "dataset_id": dataset_id
            }
            
        except Forbidden:
            error_msg = f"没有访问数据集 '{dataset_id}' 的权限"
            self.logger.warning("数据集访问权限不足", dataset_id=dataset_id)
            return {
                "success": False,
                "error": error_msg,
                "error_type": "FORBIDDEN",
                "dataset_id": dataset_id
            }
            
        except Exception as e:
            error_msg = f"探索数据集时发生错误: {str(e)}"
            self.logger.error("数据集探索失败", dataset_id=dataset_id, error=str(e))
            return {
                "success": False,
                "error": error_msg,
                "error_type": "UNKNOWN",
                "dataset_id": dataset_id
            }
    
    def _get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """
        获取数据集基本信息
        
        Args:
            dataset_id: 数据集ID
            
        Returns:
            数据集信息字典
        """
        return self.client.get_dataset_info(dataset_id)
    
    def _list_tables(
        self, 
        dataset_id: str, 
        include_details: bool = False,
        table_pattern: Optional[str] = None,
        max_tables: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出数据集中的表
        
        Args:
            dataset_id: 数据集ID
            include_details: 是否包含详细信息
            table_pattern: 表名过滤模式
            max_tables: 最大表数量
            
        Returns:
            表信息列表
        """
        table_ids = self.client.list_tables(dataset_id)
        
        result = []
        for table_id in table_ids[:max_tables]:
            # 应用表名过滤
            if table_pattern and not self._match_pattern(table_id, table_pattern):
                continue
            
            table_info = self.client.get_table_info(dataset_id, table_id)
            
            if not include_details:
                table_info.pop("schema", None)
            
            result.append(table_info)
        
        return result
    
    def _get_table_schema(self, dataset_id: str, table_id: str) -> List[Dict[str, Any]]:
        """
        获取表的结构信息
        
        Args:
            dataset_id: 数据集ID
            table_id: 表ID
            
        Returns:
            表结构字段列表
        """
        return self.client.get_table_schema(dataset_id, table_id)
    

    
    async def _arun(self, *args, **kwargs):
        """异步运行方法（暂不支持）"""
        raise NotImplementedError("BigQueryDatasetExplorer不支持异步运行")


def create_dataset_explorer_tool(client: BigQueryClient) -> BigQueryDatasetExplorer:
    """
    创建数据集探索工具实例
    
    这是一个工厂函数，用于在LangGraph工作流中创建工具实例。
    
    Args:
        client: BigQueryClient实例
        
    Returns:
        配置好的数据集探索工具实例
        
    Example:
        >>> # 在LangGraph工作流中使用
        >>> from .client import BigQueryClient
        >>> client = BigQueryClient(project_id="my-project")
        >>> explorer = create_dataset_explorer_tool(client)
        >>> result = explorer.run({
        ...     "dataset_id": "my_dataset",
        ...     "include_table_details": True,
        ...     "table_pattern": "sales_*",
        ...     "max_tables": 50
        ... })
    """
    return BigQueryDatasetExplorer(client=client)


# 为了向后兼容，提供一个简化的函数接口
def explore_dataset(
    dataset_id: str,
    client: BigQueryClient,
    include_table_details: bool = False,
    table_pattern: Optional[str] = None,
    max_tables: int = 100
) -> Dict[str, Any]:
    """
    探索BigQuery数据集的便捷函数
    
    Args:
        dataset_id: 数据集ID
        client: BigQueryClient实例
        include_table_details: 是否包含表详细信息
        table_pattern: 表名过滤模式
        max_tables: 最大表数量
        
    Returns:
        探索结果字典
        
    Example:
        >>> from .client import BigQueryClient
        >>> client = BigQueryClient(project_id="my-project")
        >>> result = explore_dataset(
        ...     "dbt_kc_ai_test",
        ...     client=client,
        ...     include_table_details=True,
        ...     table_pattern="user_*"
        ... )
        >>> if result["success"]:
        ...     print(f"找到 {len(result['tables'])} 个表")
    """
    explorer = create_dataset_explorer_tool(client)
    return explorer._run(
        dataset_id=dataset_id,
        include_table_details=include_table_details,
        table_pattern=table_pattern,
        max_tables=max_tables
    )