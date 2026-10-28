# deepresearch-py

DeepResearch 多智能体深度研究的 Python 重写项目（monorepo）。
学习目标：吃透 AI 落地的 Graph 编排架构 + 升级 Python 工程能力。

参考原型：[spring-ai-alibaba-deepresearch](https://github.com/alibaba/spring-ai-alibaba/tree/main/spring-ai-alibaba-examples/deepresearch)（Java）

## 仓库结构

```
deepresearch-py/
├── admin/               # 管理面：ruoyi-fastapi（用户/RBAC/任务管理/报告展示）
├── ai/                  # 运行面：DeepResearch AI 服务（图编排/SSE/RAG）
├── docker-compose.yml   # mysql + postgres(pgvector) + redis + 两个服务
└── README.md
```

两个服务独立开发、独立部署（各自 pyproject / uv.lock / Dockerfile），
集成点只有三个：

1. **JWT 共享**：admin 登录签发 JWT（HS512），ai 服务用同一密钥校验
2. **数据分治**：admin 用 MySQL（ruoyi_fastapi 库），ai 用 Postgres（deepresearch 库，pgvector），Redis 共享实例、db 号隔离（admin=0，ai=1）
3. **任务/文件 API**：admin 上传知识库文件后调 ai 的 ingest 接口；研究任务记录由 ai 写库、admin 展示

## 快速开始

```bash
# 1. 起中间件（或完整容器化：docker compose up -d --build）
docker compose up -d mysql postgres redis

# 2. admin 服务（端口 8000）
cd admin && uv sync && uv run uvicorn ruoyi_fastapi.main:app --reload --port 8000

# 3. ai 服务（端口 8001）
cd ai && uv sync && cp .env.example .env
uv run uvicorn deepresearch.main:app --reload --port 8001
```

## 学习路线（ai 服务）

> 详细任务清单、目标图编排与技术决策见 [ai/docs/ROADMAP.md](ai/docs/ROADMAP.md)。

| 阶段 | 内容 | 锻炼点 |
|---|---|---|
| P1 | 最小图核心：协调→规划→研究→报告，CLI 跑通 | LangGraph、Pydantic |
| P2 | SSE 流式 + interrupt 人工确认 | async generator、yield |
| P3 | 并行 researcher + pgvector RAG | asyncio.gather、检索融合 |
| P4 | 质检回环、记忆、可观测、部署 | Redis、OTel、Docker |
