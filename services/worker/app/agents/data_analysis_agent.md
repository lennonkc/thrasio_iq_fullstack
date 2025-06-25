# DataAnalysisAgent 详解

本文档详细解释 `DataAnalysisAgent` 的功能、内部逻辑、接口、输入输出以及其组件间的调用关系。

## 1. 核心功能

`DataAnalysisAgent` 是一个基于 `LangGraph` 构建的数据分析智能体。其核心功能是接收用户的自然语言查询，并自动执行一系列步骤来完成数据分析任务，最终返回结构化的结果，甚至生成数据可视化图表。

主要任务包括：
- **意图理解**: 解析用户查询，识别其分析意图（如查询数据、生成可视化等）。
- **数据模式检索**: 根据用户意图，从 BigQuery 中查找相关的表结构（Schema）。
- **SQL 生成**: 基于用户意图和相关的表结构，自动生成 SQL 查询语句。
- **查询执行**: 在 BigQuery 上执行生成的 SQL 语句。
- **结果格式化**: 将分析结果和错误信息整合成对用户友好的响应。

## 2. 工作流程 (Workflow)

该智能体的工作流程被定义为一个状态图 (StateGraph)，其中每个节点代表一个处理步骤。

```mermaid
graph TD
    A[intent_understanding] --> B{Error?}
    B -- continue --> C[schema_retrieval]
    B -- error --> H[error_handling]

    C --> D[sql_generation]
    D --> E{Error?}
    E -- continue --> F[query_execution]
    E -- error --> H

    F --> G{Error?}
    G -- continue --> J[response_formatting]
    G -- error --> H

    H --> J
    J --> K([END])

    subgraph Workflow Steps
        A
        C
        D
        F
        J
        H
    end
```

### 步骤详解:
1.  **`intent_understanding`**: 理解用户查询的意图。
2.  **`schema_retrieval`**: 根据意图检索相关的 BigQuery 表结构。
3.  **`sql_generation`**: 生成 SQL 查询。
4.  **`query_execution`**: 执行 SQL 并获取结果。
5.  **`response_formatting`**: 格式化最终的响应。
6.  **`error_handling`**: 捕获并处理工作流程中任何步骤的错误。

## 3. 核心类与接口

### `DataAnalysisAgent`
这是主类，负责初始化和编排整个工作流程。

- **`__init__(self, bigquery_client, llm_client, project_id)`**: 构造函数。
  - **`bigquery_client`**: `BigQueryClient` 实例，用于与 BigQuery 交互。
  - **`llm_client`**: 大语言模型客户端，用于意图理解和 SQL 生成。
  - **`project_id`**: Google Cloud 项目 ID。

- **`_build_workflow(self)`**: 构建 LangGraph 工作流程。

- **`async def _understand_intent(self, state)`**: 节点方法，理解用户意图。
- **`async def _retrieve_schemas(self, state)`**: 节点方法，检索表结构。
- **`async def _generate_sql(self, state)`**: 节点方法，生成 SQL。
- **`async def _execute_query(self, state)`**: 节点方法，执行查询。
- **`async def _format_response(self, state)`**: 节点方法，格式化响应。
- **`async def _handle_error(self, state)`**: 节点方法，处理错误。

### `AnalysisState` (TypedDict)
这个类定义了工作流程中传递的状态。它包含了所有步骤的输入和输出。

- **输入**:
  - `user_query: str`
  - `user_id: str`
  - `session_id: str`
- **中间状态/输出**:
  - `intent: Optional[AnalysisIntent]`
  - `relevant_schemas: List[Dict[str, Any]]`
  - `generated_sql: Optional[str]`
  - `query_results: Optional[Dict[str, Any]]`
  - `final_response: Optional[str]`
  - `execution_error: Optional[str]`

### `AnalysisIntent` (Pydantic Model)
这个数据类用于结构化地表示从用户查询中理解到的意图。

- `intent_type: str`: 意图类型 (e.g., "query", "visualization")
- `entities: List[str]`: 提及的实体 (表、字段)
- `metrics: List[str]`: 指标
- `dimensions: List[str]`: 维度
- `filters: Dict[str, Any]`: 过滤条件

## 4. 组件调用关系

`DataAnalysisAgent` 依赖多个外部客户端和内部管理器来完成其工作。

```mermaid
graph LR
    subgraph DataAnalysisAgent
        direction LR
        Agent[_build_workflow] --> Workflow
        Workflow -- invokes --> Node1[_understand_intent]
        Workflow -- invokes --> Node2[_retrieve_schemas]
        Workflow -- invokes --> Node3[_generate_sql]
        Workflow -- invokes --> Node4[_execute_query]
    end

    subgraph External Clients
        LLM[LLM Client]
        BQ[BigQueryClient]
    end

    subgraph Internal Managers
        SchemaMgr[SchemaManager]
        QueryBuilder[QueryBuilder]
    end

    Node1 -- uses --> LLM
    Node2 -- uses --> SchemaMgr
    Node3 -- uses --> QueryBuilder
    Node3 -- uses --> LLM
    Node4 -- uses --> BQ

    SchemaMgr -- uses --> BQ

    style Agent fill:#f9f,stroke:#333,stroke-width:2px
    style Workflow fill:#ccf,stroke:#333,stroke-width:2px
```

### 调用关系详解:
- **`DataAnalysisAgent`** 是核心协调者。
- **`_understand_intent`** 和 **`_generate_sql`** 节点会调用 **LLM Client** 来处理自然语言和生成代码。
- **`_retrieve_schemas`** 节点使用 **`SchemaManager`**，而 `SchemaManager` 内部调用 **`BigQueryClient`** 来获取元数据。
- **`_execute_query`** 节点直接使用 **`BigQueryClient`** 来运行查询。
- **`QueryBuilder`** 是一个辅助工具，用于以编程方式构建 SQL 语句，主要在 **`_generate_sql`** 中使用。