FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY contracts/ contracts/
COPY dispute-mcp-server/ dispute-mcp-server/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --package dispute-mcp-server

CMD ["uv", "run", "--package", "dispute-mcp-server", "python", "-m", "dispute_mcp_server.main"]
