FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# 先装依赖再拷源码，利用 Docker 层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY prompts ./prompts

EXPOSE 8001

CMD ["uv", "run", "--no-sync", "uvicorn", "deepresearch.main:app", "--host", "0.0.0.0", "--port", "8001"]
