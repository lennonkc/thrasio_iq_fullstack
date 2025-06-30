# 企业级多 Agent 系统：最终项目目录结构方案

## 1. 设计理念

本方案旨在结合 **方案 1 的简洁性** 和 **方案 2 的架构严谨性**，为企业级多 Agent 系统提供一个清晰、可扩展且易于维护的 Monorepo 项目结构。

**核心原则:**

1.  **服务化 (Service-Oriented):** 明确分离可独立部署的单元（如 API 服务、后台 Worker 服务、前端应用），使其与 GCP Cloud Run 上的部署形态一一对应。
2.  **关注点分离 (Separation of Concerns):** 在服务内部，严格分离 API 路由、业务逻辑、数据模型和 Agent 定义。
3.  **代码共享 (Shared Code):** 提供一个中心化的 `shared` 包，用于存放跨服务共享的 Pydantic 模型、工具函数或常量。
4.  **基础设施即代码 (IaC):** 将所有云资源配置通过 Terraform 集中管理，实现环境的一致性和可追溯性。
5.  **清晰的开发体验:** 根目录保持整洁，通过 `Makefile` 和 `docker-compose.yml` 简化本地开发和测试流程。

---

## 2. 最终目录结构

```plaintext
thrasio-iq/
├── .github/                    # CI/CD 工作流 (GitHub Actions)
│   └── workflows/
│       ├── ci.yml              # 持续集成 (测试, Lint, 构建)
│       └── cd.yml              # 持续部署 (部署到 GCP)
│
├── docs/                       # 项目文档 (如本文件)
│   ├── Enterprise_Multi_Agent_System_Research.md
│   └── ...
│
├── iac/                        # 基础设施即代码 (Terraform)
│   ├── environments/           # 各环境 (dev, staging, prod) 的变量配置
│   │   ├── dev/
│   │   └── prod/
│   ├── modules/                # 可复用的 Terraform 模块 (如 cloud_run, firestore)
│   └── main.tf                 # 根 Terraform 配置
│
├── services/                   # 核心：所有可独立部署的服务
│   ├── api/                    # FastAPI 后端 API 服务 (同步)
│   │   ├── app/
│   │   │   ├── api/            # API 端点/路由 (v1, v2...)
│   │   │   ├── core/           # 核心配置 (Config, Security)
│   │   │   ├── schemas/        # Pydantic 输入/输出模型
│   │   │   ├── services/       # 业务逻辑层
│   │   │   └── main.py         # FastAPI 应用入口
│   │   ├── tests/              # 自动化测试 (unit, integration)
│   │   ├── .env.example
│   │   ├── Dockerfile
│   │   └── pyproject.toml      # 服务独立的依赖管理
│   │
│   ├── worker/                 # Agent Worker 后台服务 (异步)
│   │   ├── app/
│   │   │   ├── agents/         # LangGraph Agent 定义
│   │   │   ├── tools/          # Agent 可用的自定义工具
│   │   │   ├── workflows/      # LangGraph 图的编排
│   │   │   ├── processors/     # 任务处理器 (如 Pub/Sub 监听器)
│   │   │   └── main.py         # Worker 服务入口
│   │   ├── tests/
│   │   ├── .env.example
│   │   ├── Dockerfile
│   │   └── pyproject.toml      # 服务独立的依赖管理
│   │
│   └── frontend/               # Next.js 前端应用
│       ├── app/                # Next.js App Router
│       ├── components/         # 可复用的 UI 组件
│       ├── lib/                # 辅助函数, Hooks, API 客户端
│       ├── public/
│       ├── .env.local.example
│       ├── package.json
│       └── tsconfig.json
│
├── shared/                     # 跨 Python 服务的共享代码库
│   ├── schemas/                # 共享的 Pydantic Schemas
│   ├── constants/              # 共享常量
│   └── utils/                  # 共享工具函数
│
├── .dockerignore
├── .gitignore
├── docker-compose.yml          # 用于本地一键启动所有服务
├── Makefile                    # 常用命令快捷方式 (test, build, run)
└── README.md                   # 项目总览、架构图和开发指南
```

---

## 3. 目录结构解析

*   **`services/`**: 这是项目的核心。与方案 2 一样，它将系统拆分为多个独立的服务。这种结构的最大好处是，`api` 和 `worker` 可以作为两个不同的 Docker 镜像构建，并部署到两个独立的 Cloud Run 服务上，允许它们独立扩展和更新。
    *   每个服务（如 `api`, `worker`）都是一个完整的 Python 项目，拥有自己的 `pyproject.toml` 来管理依赖，这解决了方案 2 中根目录依赖混乱的问题。
    *   `frontend` 也被视为一个服务，遵循标准的 Next.js 结构。

*   **`iac/`**: 借鉴了方案 1 的命名，清晰地表示“基础设施即代码”。其内部结构（`environments`, `modules`）则采纳了方案 2 的最佳实践，非常适合多环境管理。

*   **`shared/`**: 这是方案 2 的一个关键优势。我们将其保留并简化，专门用于 Python 服务间的代码共享。例如，API 服务和 Worker 服务可能需要使用相同的 Pydantic 数据模型，将它们定义在 `shared/schemas` 中可以避免代码重复。

*   **根目录**: 保持了最大程度的整洁。
    *   `docker-compose.yml`: 用于在本地开发时，一键启动 `api`, `worker`, `frontend` 以及数据库等依赖，极大提升开发效率。
    *   `Makefile`: 提供了诸如 `make build`, `make test-api`, `make run-dev` 等快捷命令，统一了项目操作入口。
    *   `README.md`: 作为项目的入口点，应包含项目简介、架构图、本地环境设置指南和部署流程。
