"""uvicorn entrypoint for transaction-agent."""

from __future__ import annotations

import uvicorn

from transaction_agent.api import app

__all__ = ["app", "main"]


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8010)


if __name__ == "__main__":
    main()
