"""数据分析代理的状态管理类"""

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class AppState(TypedDict):
    """数据分析工作流的共享状态"""

    # 基础配置信息
    project_id: str

    # 数据集相关状态
    available_datasets: List[str]
    selected_dataset: Optional[str]
    tables_in_dataset: List[str]
    table_schemas: Optional[Dict[str, List[Dict[str, Any]]]]

    # 用户任务相关
    user_task: Optional[str]
    filtered_task: Optional[str]  # 安全过滤后的任务

    # 查询生成和执行
    generated_queries: Optional[List[str]]
    test_results: Optional[List[Dict[str, Any]]]  # 小规模测试结果
    query_results: Optional[List[Dict[str, Any]]]  # 完整查询结果

    # 分析和结果
    analysis_report: Optional[str]

    # 错误处理
    error_message: Optional[str]
    retry_count: int

    # LangGraph消息历史
    messages: List[BaseMessage]

    # 当前步骤追踪
    current_step: str

    # 外部记忆相关
    memory_keys: Optional[List[str]]  # 存储到外部记忆的键列表
