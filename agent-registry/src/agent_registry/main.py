"""uvicorn entrypoint for agent-registry."""

from __future__ import annotations

import uvicorn

from agent_registry.api import app

__all__ = ["app", "main"]


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8020)


if __name__ == "__main__":
    main()
