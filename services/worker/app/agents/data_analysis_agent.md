# 需求概述
我想要基于LangGraph和python-bigquery构建以下工作流, 目的是让普通用户也可以智能分析Bigquery的数据库.
- 目前是最初版本, 不需要做前端页面, 在命令行实现交互即可.
- 编写代码时注意使用context7 帮助你来保证代码兼容性和正确性
- 单个py文件不宜过长, 最好在 300 行内, 如果超过 300 行, 要考虑适当拆分设计
- 代码注释使用中文
- 如需利用python-bigquery构建额外的Bigquery tools, 请在"services/worker/app/tools"下构建
- langgraph的agent请在"services/worker/app/agents"下构建
- 每执行完成一个阶段, 你需要对"services/worker/app/agents/data_analysis_agent.md"的内容进行更新和标记完成情况

# 工作流信息
1. welcome信息: 表格方式显示所有dataset
2. 接受用户所选择的dataset. (用命令行的序号完成交互)
3. 表格显示这个dataset下的所有tables, 并询问用户输入分析任务 (用命令行的序号完成交互)
4. 任务过滤, 保证安全(仅可读,不可创建不可删除不可修改)
5. 读取tables的scheme
6. 意图分析和query生成
7. query数据小规模测试, 最大返回前 10 条数据(自测试和自验证, 用户不可见)(所有query都需要简单测试, 通过后再进行下一步, 若失败则带着失败信息回到第六步)
8. 汇总执行所有query, 收集所有结果 (如触发最大Token, 将临时结果先进行分析后存储到外部记忆, 外部记忆存在"services/worker/app/memory")
9. 为用户呈现智能分析结果

# prompt设计

将所有Prompt都独立放到"services/worker/app/prompt"下, 实现更好的分离

# 其他信息

- 目前命令行已通过config实现了和Bigquery的对接.用于Bigquery的project_id是"thrasio-dev-data-wh-7ee095", 这些已经在config文件处理好了
- 错误处理和边界情况处理：
  BigQuery连接失败或认证失败怎么办？-> 结束任务
  用户输入的dataset或table名称不存在怎么办？-> 重新询问用户输入
  用户输入的分析任务意图不明，无法生成有效SQL怎么办？-> 重新询问用户输入

# LangGraph 状态管理

下面提供了一个工作流中的所有节点共享一个状态对象的案例建议, 你可以根据实际情况进行调整和优化
其结构定义如下 (使用Python TypedDict或Pydantic):

class AppState(TypedDict):
    project_id: str
    available_datasets: List[str]
    selected_dataset: Optional[str]
    tables_in_dataset: List[str]
    table_schemas: Optional[Dict[str, List[str]]]
    user_task: Optional[str]
    generated_queries: Optional[List[str]]
    query_results: Optional[List[Dict]]
    error_message: Optional[str]
    analysis_report: Optional[str]