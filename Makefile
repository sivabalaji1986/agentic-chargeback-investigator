.PHONY: install lock format lint typecheck test mcp-test mcp-run registry-test registry-run verify ui-install ui-build clean

install:
	uv sync --all-packages

lock:
	uv lock

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

test:
	uv run pytest

mcp-test:
	uv run pytest dispute-mcp-server/tests -v

mcp-run:
	uv run --package dispute-mcp-server python -m dispute_mcp_server.main

registry-test:
	uv run pytest agent-registry/tests -v

registry-run:
	uv run --package agent-registry python -m agent_registry.main

ui-install:
	cd investigator-ui && npm install

ui-build:
	cd investigator-ui && npm run build

verify:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy .
	uv run pytest
	$(MAKE) ui-install
	$(MAKE) ui-build

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '.ruff_cache' -exec rm -rf {} +
	rm -rf investigator-ui/dist investigator-ui/node_modules
