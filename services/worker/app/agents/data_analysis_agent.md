# 需求概述
我想要基于LangGraph和python-bigquery构建以下工作流, 目的是让普通用户也可以智能分析Bigquery的数据库.
- 目前是最初版本, 不需要做前端页面, 在命令行实现交互即可.
- 编写代码时注意使用context7 帮助你来保证代码兼容性和正确性
- 单个py文件不宜过长, 最好在 300 行内, 如果超过 300 行, 要考虑适当拆分设计
- 代码注释使用中文
- 如需利用python-bigquery构建额外的Bigquery tools, 请在"services/worker/app/tools"下构建
- langgraph的agent请在"services/worker/app/agents"下构建
- 每执行完成一个阶段, 你需要对"services/worker/app/agents/data_analysis_agent.md"的内容进行更新和标记完成情况

## 实现进度

### 已完成阶段 ✅

1. **状态管理系统** (`app/agents/state.py`) - 完成
   - 创建了AppState类型定义，包含所有工作流状态
   - 支持项目配置、数据集选择、表结构、查询生成等状态管理
   - 集成了外部记忆键管理和错误处理状态

2. **提示词模板系统** (`app/prompts/analysis_prompts.py`) - 完成
   - 任务安全过滤提示词 (TASK_SAFETY_FILTER_PROMPT)
   - 意图分析和SQL生成提示词 (INTENT_ANALYSIS_PROMPT) 
   - 分析报告生成提示词 (ANALYSIS_REPORT_PROMPT)
   - 错误分析和修复提示词 (ERROR_ANALYSIS_PROMPT)

3. **外部记忆存储** (`app/memory/external_memory.py`) - 完成
   - 实现了ExternalMemory类用于存储大型查询结果
   - 支持会话管理、数据检索、过期清理功能
   - 专门处理Token限制场景下的数据存储

4. **核心代理逻辑** (`app/agents/data_analysis_agent.py`) - 完成
   - 创建了DataAnalysisAgent主类，继承BaseAgent
   - 实现了LangGraph工作流创建和状态管理
   - 集成了BigQuery客户端和LLM模型
   - 支持同步和异步流式执行

5. **工作流节点实现** (`app/agents/workflow_nodes.py`, `workflow_nodes_part2.py`) - 完成
   - welcome_node: 显示数据集列表
   - select_dataset_node: 交互式数据集选择
   - show_tables_node: 显示表格信息
   - get_user_task_node: 获取用户分析任务
   - filter_task_node: 安全过滤检查
   - read_schemas_node: 读取表结构
   - generate_queries_node: LLM生成SQL查询
   - test_queries_node: 小规模查询测试
   - execute_queries_node: 完整查询执行
   - generate_report_node: 生成智能分析报告
   - handle_error_node: 错误处理

6. **命令行交互界面** (`app/cli.py`) - 完成
   - 实现了DataAnalysisCLI类
   - 支持交互式和流式两种运行模式
   - 集成了欢迎界面、系统信息显示、帮助文档
   - 完整的用户确认和错误处理流程

7. **安全过滤和错误处理** - 完成
   - LLM驱动的任务安全检查，防止危险SQL操作
   - 多级重试机制 (最多3次重试)
   - 完整的异常捕获和用户友好错误信息
   - 自动查询验证和修复建议

8. **代码质量优化** - 完成
   - 通过black代码格式化
   - 通过isort导入排序
   - 模块化设计，单文件代码量控制在300行内
   - 完整的类型注解和文档字符串

## 使用方法

### 启动系统
```bash
# 交互式模式
uv run python app/cli.py

# 流式模式(显示中间步骤)
uv run python app/cli.py --streaming
```

### 完整工作流程 ✅

1. **welcome信息**: 表格方式显示所有dataset ✅
2. **接受用户所选择的dataset**: 用命令行的序号完成交互 ✅
3. **表格显示tables**: 显示dataset下的所有tables, 并询问用户输入分析任务 ✅
4. **任务过滤**: 保证安全(仅可读,不可创建不可删除不可修改) ✅
5. **读取表结构**: 读取tables的schema ✅
6. **意图分析和query生成**: LLM分析用户意图并生成SQL ✅
7. **query小规模测试**: 最大返回前10条数据进行验证，失败则重新生成 ✅
8. **汇总执行查询**: 收集所有结果，大型结果存储到外部记忆 ✅
9. **智能分析结果**: 为用户呈现结构化的分析报告 ✅

## 技术架构总结

### 核心组件 ✅
- **LangGraph工作流引擎**: 状态机驱动的数据分析流程
- **BigQuery集成**: 通过app/tools/bigquery/client.py实现数据查询
- **LLM集成**: 使用Vertex AI (gemini-2.5-flash) 进行意图分析和报告生成
- **外部记忆系统**: 处理大型查询结果的存储和检索
- **安全过滤**: LLM驱动的SQL安全检查，防止危险操作

### 项目配置 ✅
- **BigQuery项目ID**: "thrasio-dev-data-wh-7ee095"
- **LLM项目ID**: "thrasio-dev-ai-agent"  
- **包管理**: uv (替代pip)
- **Python环境**: 3.11+ (.venv虚拟环境)

### 错误处理策略 ✅
- **BigQuery连接失败**: 优雅退出并显示错误信息
- **数据集/表不存在**: 重新提示用户选择
- **任务意图不明**: 最多3次重试，然后转入错误处理
- **查询执行失败**: 自动跳过失败查询，继续执行其他查询

### 已实现的LangGraph状态管理 ✅

```python
class AppState(TypedDict):
    project_id: str
    available_datasets: List[str]
    selected_dataset: Optional[str]
    tables_in_dataset: List[str]
    table_schemas: Optional[Dict[str, List[Dict[str, Any]]]]
    user_task: Optional[str]
    filtered_task: Optional[str]  # 安全过滤后的任务
    generated_queries: Optional[List[str]]
    test_results: Optional[List[Dict[str, Any]]]  # 小规模测试结果
    query_results: Optional[List[Dict[str, Any]]]  # 完整查询结果
    analysis_report: Optional[str]
    error_message: Optional[str]
    retry_count: int
    messages: List[BaseMessage]
    current_step: str
    memory_keys: Optional[List[str]]  # 外部记忆键列表
```

## 总结

✅ **任务完成状态**: 100%完成

根据需求文档，所有9个工作流步骤都已成功实现：
1. 数据集展示 ✅
2. 交互式数据集选择 ✅  
3. 表格展示和任务获取 ✅
4. 安全任务过滤 ✅
5. 表结构读取 ✅
6. 意图分析和SQL生成 ✅
7. 查询小规模测试 ✅
8. 完整查询执行和外部记忆存储 ✅
9. 智能分析报告生成 ✅

系统具备完整的错误处理、安全过滤、重试机制，代码经过格式化和质量检查，可投入使用。