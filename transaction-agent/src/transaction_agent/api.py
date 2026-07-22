"""FastAPI app: temporary intake, real AG-UI run, and investigator-action
endpoints.

/agent/run speaks the actual AG-UI wire protocol (RunAgentInput in,
SSE-encoded events out) -- confirmed during design research that ag_ui.core
models use camelCase JSON aliases (threadId, runId, forwardedProps), which
FastAPI/Pydantic handle natively. case_id travels in
input.forwarded_props["case_id"] since RunAgentInput has no case-specific
field of its own.
"""

from __future__ import annotations

import logging

from ag_ui.core import RunAgentInput
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from chargeback_contracts.decisions import InvestigatorDecision
from transaction_agent.config import load_settings
from transaction_agent.llm_client import ExplanationClient, OllamaExplanationClient
from transaction_agent.mcp_client import TransactionLookupError, get_case_and_transaction
from transaction_agent.service import run_investigation

logger = logging.getLogger("transaction_agent")

DEFAULT_INTAKE_CASE_ID = "CASE-1001"


class IntakeRequest(BaseModel):
    """Temporary intake payload -- the piece Prompt 6's Orchestrator replaces."""

    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, default=DEFAULT_INTAKE_CASE_ID)


async def _lookup_or_404(case_id: str) -> tuple[dict[str, object], dict[str, object]]:
    try:
        return await get_case_and_transaction(case_id)
    except TransactionLookupError as exc:
        logger.warning(
            "investigation lookup failed case_id=%s error=%s", case_id, type(exc).__name__
        )
        raise HTTPException(status_code=404, detail="case not found") from exc


def create_app(*, explanation_client: ExplanationClient | None = None) -> FastAPI:
    settings = load_settings()
    if explanation_client is None:
        explanation_client = OllamaExplanationClient(
            base_url=settings.ollama_base_url, model=settings.ollama_text_model
        )

    app = FastAPI(title=settings.service_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/agent/run")
    async def agent_run(run_input: RunAgentInput) -> StreamingResponse:
        forwarded = run_input.forwarded_props if isinstance(run_input.forwarded_props, dict) else {}
        case_id = forwarded.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise HTTPException(status_code=422, detail="forwardedProps.case_id is required")

        case_data, transaction_data = await _lookup_or_404(case_id)
        generator = run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id=run_input.thread_id,
            run_id=run_input.run_id,
            explanation_client=explanation_client,
        )
        return StreamingResponse(generator, media_type="text/event-stream")

    @app.post("/intake")
    async def intake(request: IntakeRequest) -> StreamingResponse:
        import uuid

        case_data, transaction_data = await _lookup_or_404(request.case_id)
        thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        generator = run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id=thread_id,
            run_id=run_id,
            explanation_client=explanation_client,
        )
        return StreamingResponse(generator, media_type="text/event-stream")

    @app.post("/actions/decision", status_code=204)
    async def actions_decision(decision: InvestigatorDecision) -> Response:
        logger.info(
            "investigator_decision case_id=%s action=%s investigator_id=%s",
            decision.case_id,
            decision.selected_action.value,
            decision.investigator_id,
        )
        return Response(status_code=204)

    return app


app = create_app()
