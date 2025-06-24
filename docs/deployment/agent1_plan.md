# BigQuery x Looker 数据分析 Agent 执行计划

## 项目概述

本执行计划基于 `/Users/KC/KCodes/thrasio_iq_backend/docs/development/agent1.md` 文档，旨在逐步实现 BigQuery x Looker 数据分析 Agent。该 Agent 是 Thrasio IQ 企业级多 Agent 系统的核心组件，专门负责处理数据查询、分析和可视化任务。

## 阶段一：基础环境搭建

### 步骤 1.1：项目目录结构创建
**目标**：创建 Agent 相关的目录结构
**具体任务**：
- 在 `services/worker/app/` 下创建以下目录结构：
  - `agents/`
  - `tools/bigquery/`
  - `tools/looker/`
  - `workflows/`
  - `memory/`
  - `processors/`
- 创建对应的 `__init__.py` 文件

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已创建所有必要的目录结构和初始化文件
```

### 步骤 1.2：依赖包安装和配置
**目标**：安装和配置必要的 Python 依赖包
**具体任务**：
- 更新 `requirements.txt` 添加以下依赖：
  - `langgraph`
  - `google-cloud-bigquery`
  - `google-cloud-firestore`
  - `google-cloud-pubsub`
  - `google-cloud-secret-manager`
  - `pydantic-ai`
  - `llamaindex`
  - `langsmith`
- 配置 Google Cloud 认证

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已创建 requirements.txt 文件并添加所有必要依赖包（认证部分需要手动配置）
```

## 阶段二：核心组件开发

### 步骤 2.1：基础 Agent 类实现
**目标**：实现基础 Agent 抽象类
**具体任务**：
- 创建 `services/worker/app/agents/base_agent.py`
- 定义 Agent 基础接口和通用方法
- 实现状态管理和错误处理机制

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已实现 BaseAgent 抽象类，包含状态管理、错误处理和通用方法
```

### 步骤 2.2：BigQuery 工具开发
**目标**：实现 BigQuery 相关工具类
**具体任务**：
- 创建 `services/worker/app/tools/bigquery/client.py`
- 实现 BigQuery 客户端封装
- 创建 `query_builder.py` 实现 SQL 查询构建器
- 创建 `schema_manager.py` 实现 Schema 管理

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已实现完整的 BigQuery 工具集，包括客户端、查询构建器和 Schema 管理器
```

### 步骤 2.3：Looker 工具开发
**目标**：实现 Looker API 集成工具
**具体任务**：
- 创建 `services/worker/app/tools/looker/client.py`
- 实现 Looker API 客户端
- 创建 `dashboard_manager.py` 实现仪表板管理
- 创建 `visualization.py` 实现可视化配置

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已实现完整的 Looker 工具集，包括 API 客户端、仪表板管理器和可视化管理器
```

### 步骤 2.4：LangGraph 工作流实现
**目标**：实现数据分析工作流
**具体任务**：
- 创建 `services/worker/app/workflows/data_analysis_workflow.py`
- 定义 AnalysisState 状态类
- 实现工作流节点：意图理解、Schema检索、SQL生成、查询执行、可视化创建、响应格式化
- 配置节点间的边和条件

**执行情况**：
```
[✓] 已完成
[ ] 进行中
[ ] 未开始
备注：已实现完整的 LangGraph 数据分析工作流，包含所有必要的节点和状态管理
```

## 阶段三：记忆和处理器开发

### 步骤 3.1：记忆管理系统
**目标**：实现对话记忆和向量记忆
**具体任务**：
- 创建 `services/worker/app/memory/conversation_memory.py`
- 实现基于 Firestore 的会话状态管理
- 创建 `vector_memory.py` 实现向量记忆（Schema 检索）
- 集成 Vertex AI Vector Search

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 3.2：数据分析处理器
**目标**：实现数据分析任务处理器
**具体任务**：
- 创建 `services/worker/app/processors/data_analysis_processor.py`
- 实现异步任务处理逻辑
- 集成 Pub/Sub 消息处理
- 实现错误处理和重试机制

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 3.3：数据分析 Agent 主类
**目标**：实现完整的数据分析 Agent
**具体任务**：
- 创建 `services/worker/app/agents/data_analysis_agent.py`
- 继承基础 Agent 类
- 集成所有工具和工作流
- 实现主要的分析方法

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

## 阶段四：配置和部署

### 步骤 4.1：Docker 配置
**目标**：配置容器化部署
**具体任务**：
- 更新 `infrastructure/docker/worker/Dockerfile`
- 配置环境变量和依赖
- 创建 docker-compose 配置用于本地测试

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 4.2：Cloud Run 部署配置
**目标**：配置 Google Cloud Run 部署
**具体任务**：
- 创建 Cloud Run 服务配置
- 配置环境变量和密钥管理
- 设置自动扩缩容参数
- 配置健康检查

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 4.3：监控和日志配置
**目标**：配置监控和可观测性
**具体任务**：
- 集成 LangSmith 进行 AI 追踪
- 配置 Google Cloud Logging
- 设置性能监控指标
- 创建告警规则

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

## 阶段五：测试和优化

### 步骤 5.1：单元测试
**目标**：编写和执行单元测试
**具体任务**：
- 在 `services/worker/tests/` 下创建测试文件
- 为每个工具类编写单元测试
- 测试工作流节点功能
- 配置测试数据和模拟服务

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 5.2：集成测试
**目标**：端到端集成测试
**具体任务**：
- 创建集成测试场景
- 测试完整的数据分析流程
- 验证 BigQuery 和 Looker 集成
- 测试错误处理和恢复机制

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 5.3：性能优化
**目标**：优化系统性能
**具体任务**：
- 实现查询缓存机制
- 优化 SQL 查询性能
- 配置连接池
- 实现批处理优化

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

## 阶段六：安全和文档

### 步骤 6.1：安全加固
**目标**：实现安全控制措施
**具体任务**：
- 实现数据访问控制
- 配置 JWT 验证
- 设置速率限制
- 实现审计日志

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

### 步骤 6.2：文档完善
**目标**：完善项目文档
**具体任务**：
- 更新 API 文档
- 编写部署指南
- 创建用户使用手册
- 编写故障排除指南

**执行情况**：
```
[ ] 已完成
[ ] 进行中
[ ] 未开始
备注：
```

## 后续编码提示 (Prompt for Future Coding)

当你开始具体的代码实现时，请遵循以下指导原则：

### 代码实现要求：
1. **严格遵循项目目录结构**：按照 `services/worker/app/` 下的规划目录创建文件
2. **使用类型提示**：所有函数和类都要有完整的类型注解
3. **异常处理**：每个外部调用都要有适当的异常处理
4. **日志记录**：关键操作都要有结构化日志
5. **配置管理**：使用环境变量和 Secret Manager 管理敏感信息

### 技术栈集成：
- **LangGraph**：用于工作流状态管理，确保每个节点都有清晰的输入输出定义
- **Vertex AI**：使用 Gemini Pro 进行意图理解和 SQL 生成
- **BigQuery**：使用官方 Python 客户端，注意查询优化和成本控制
- **Looker**：使用 REST API，注意认证和权限管理
- **Firestore**：用于会话状态存储，设计合理的文档结构

### 关键实现点：
1. **工作流设计**：确保每个节点都是幂等的，支持重试和恢复
2. **错误处理**：区分可重试错误和不可重试错误
3. **性能考虑**：实现适当的缓存和连接池
4. **安全性**：验证所有输入，使用参数化查询防止注入

### 测试策略：
- 为每个工具类编写单元测试
- 使用模拟对象测试外部服务集成
- 创建端到端测试验证完整流程

请在实现过程中保持代码的模块化和可测试性，确保每个组件都可以独立测试和部署。

---

**注意**：此执行计划将作为后续开发的指导文档，请在每个步骤完成后更新执行情况，并记录遇到的问题和解决方案。
        