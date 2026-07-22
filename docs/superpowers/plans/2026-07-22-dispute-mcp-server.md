# Dispute MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `dispute-mcp-server` — a single FastMCP 3.4.4 server exposing 13 tools across 4 logical groups (case, transaction, customer, merchant), backed by deterministic, cross-referenced seeded mock data. Enterprise data access only — no business decisions, no orchestration.

**Architecture:** `repository.py` owns seeded data (from `seed_data.py`) behind typed lookup methods; `tools/*_tools.py` modules each export one `register_*_tools(mcp, repository, logger)` function containing `@mcp.tool`-decorated closures; `main.py` creates the `FastMCP` instance, the repository, and calls all four register functions. Local Pydantic models (`models.py`) represent every read tool's return shape; the two write tools reuse `chargeback_contracts.mcp`'s existing write-side envelope contracts as-is.

**Tech Stack:** Python 3.13, `fastmcp==3.4.4`, Pydantic v2, the existing `contracts` workspace package, `uv` workspace.

## Global Constraints

- Enterprise data access only — no business decisions, no orchestration, no Agent Registry, no A2A, no AG-UI/A2UI, no RAG/Ollama, no recommendation rules, no specialist agent logic.
- All responses come from deterministic seeded data — no live integrations, no real network I/O anywhere (including tests).
- Reuse `chargeback_contracts.mcp.UpdateCaseStatusRequest`, `CreateAuditEntryRequest`, `McpWriteResponse`, `McpStatus`, `McpErrorInfo` as-is for `update_case`/`write_audit` — these are generic envelopes with no business-schema tension. Do NOT reuse `GetCaseResponse`/`GetTransactionResponse` for the 11 read tools (deliberately minimal Prompt-2 placeholders); define new local models in `dispute-mcp-server/src/dispute_mcp_server/models.py` instead. Do NOT add anything to `chargeback_contracts` in this prompt.
- Reuse `chargeback_contracts.skills.DisputeType` for any dispute-type field in local models — a safe, already-shared enum, not a new business schema.
- Read-tool identifiers not found raise a local `NotFoundError`, which FastMCP surfaces to callers as `fastmcp.exceptions.ToolError` (confirmed by direct research). Write tools catch `NotFoundError` internally and return a `McpWriteResponse(status=McpStatus.FAILURE, ...)` instead of raising, since that contract exists precisely to represent success/failure without an exception.
- Logging must record tool name, the relevant ID parameter, success/failure, and duration — never full record contents, free-text comments, or raw exception bodies.
- Pre-existing, already-committed repo state must not be touched: the `.gitignore` modification and `tmp/prompts/Prompt01.md` / `Prompt02.md` / `Prompt03-Agent-Registry.md`.
- Commit workflow for this batch (explicit user instruction): every created/modified file gets its own `git add <file> && git commit`, with **no** `docs/COMMIT_LOG.md` touch until the final task, which the controller writes directly (not a fresh subagent — lesson carried from Prompt 1's premature-changelog incident).
- `make verify` must stay green throughout (ruff format-check, ruff lint, strict mypy, full pytest suite, `investigator-ui` build).

---

### Task 1: Add dispute-mcp-server dependencies

**Files:**
- Modify: `dispute-mcp-server/pyproject.toml`

**Interfaces:**
- Produces: `fastmcp`, `pydantic`, and the workspace-local `contracts` package available to every later task.

- [ ] **Step 1: Update `dispute-mcp-server/pyproject.toml`**

Current content (from Prompt 1):
```toml
[project]
name = "dispute-mcp-server"
version = "0.1.0"
description = "Mock enterprise data exposed through MCP"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/dispute_mcp_server"]
```

Replace with:
```toml
[project]
name = "dispute-mcp-server"
version = "0.1.0"
description = "Mock enterprise data exposed through MCP"
requires-python = ">=3.13"
dependencies = [
    "fastmcp==3.4.4",
    "pydantic>=2.13",
    "contracts",
]

[tool.uv.sources]
contracts = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/dispute_mcp_server"]
```

- [ ] **Step 2: Lock and sync**

Run: `uv lock && uv sync --all-packages`
Expected: resolves cleanly. `fastmcp==3.4.4` was confirmed to exist on the live PyPI registry during design research (2026-07-22). If resolution fails, STOP and report BLOCKED with the exact error rather than substituting a version.

- [ ] **Step 3: Commit**

```bash
git add dispute-mcp-server/pyproject.toml uv.lock
git commit -m "chore: add dispute-mcp-server dependencies (fastmcp, contracts)"
```

---

### Task 2: `models.py` — local read-tool response models

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/models.py`

**Interfaces:**
- Consumes: `chargeback_contracts.skills.DisputeType`.
- Produces: `CaseRecord`, `TransactionRecord`, `AuthorizationRecord`, `SettlementRecord`, `RefundOrReversalRecord`, `CustomerProfileRecord`, `PriorDisputeRecord`, `RefundHistoryEntry`, `MerchantEvidenceRecord`, `DeliveryDetailsRecord`, `CancellationDetailsRecord`, `AuditRecord` — consumed by `repository.py`, `seed_data.py`, and every `tools/*_tools.py` module.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/models.py`**

```python
"""Local response models for dispute-mcp-server's read tools.

These are package-owned, not part of chargeback_contracts: Prompt 2
deliberately left the case/transaction/customer/merchant business schema
undefined, and this package is where that schema now lives. Write-tool
requests/responses instead reuse chargeback_contracts.mcp's existing
envelope contracts directly (see tools/case_tools.py) — those are generic
enough to need no business-specific richness of their own.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from chargeback_contracts.skills import DisputeType


class DisputeMcpModel(BaseModel):
    """Base class for every local response model in this package."""

    model_config = ConfigDict(extra="forbid")


class CaseRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    dispute_type: DisputeType
    status: str = Field(min_length=1)
    opened_at: datetime
    amount: Decimal
    currency: str


class TransactionRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    amount: Decimal
    currency: str
    posted_at: datetime
    description: str = Field(min_length=1)


class AuthorizationRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    authorization_code: str = Field(min_length=1)
    authorized_at: datetime
    amount: Decimal
    currency: str
    approved: bool


class SettlementRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    settlement_id: str = Field(min_length=1)
    settled_at: datetime
    amount: Decimal
    currency: str


class RefundOrReversalRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    refund_id: str = Field(min_length=1)
    refunded_at: datetime
    amount: Decimal
    currency: str
    reason: str = Field(min_length=1)


class CustomerProfileRecord(DisputeMcpModel):
    customer_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    customer_since: datetime
    tenure_days: int = Field(ge=0)


class PriorDisputeRecord(DisputeMcpModel):
    dispute_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    dispute_type: DisputeType
    outcome: str = Field(min_length=1)
    resolved_at: datetime


class RefundHistoryEntry(DisputeMcpModel):
    refund_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    amount: Decimal
    currency: str
    refunded_at: datetime


class MerchantEvidenceRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    acknowledgement: bool
    evidence_summary: str = Field(min_length=1)
    submitted_at: datetime


class DeliveryDetailsRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    delivered: bool
    delivery_date: datetime | None = None
    carrier: str | None = None
    tracking_number: str | None = None


class CancellationDetailsRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    cancelled: bool
    cancellation_date: datetime | None = None
    confirmation_reference: str | None = None


class AuditRecord(DisputeMcpModel):
    audit_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    event_description: str = Field(min_length=1)
    recorded_at: datetime
    idempotency_key: str = Field(min_length=1)
```

- [ ] **Step 2: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/models.py
git commit -m "feat: add local response models for dispute-mcp-server read tools"
```

---

### Task 3: `seed_data.py` — deterministic, cross-referenced mock data

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/seed_data.py`

**Interfaces:**
- Consumes: every model from `models.py`, `DisputeType` from `chargeback_contracts.skills`.
- Produces: module-level constants consumed by `repository.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/seed_data.py`**

```python
"""Deterministic, internally-consistent seeded mock data.

Every ID below is stable and cross-referenced (case -> transaction ->
customer -> merchant) so later prompts can rely on the same identifiers.
This is the only place mock data is defined; repository.py only reads it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from chargeback_contracts.skills import DisputeType

from dispute_mcp_server.models import (
    AuthorizationRecord,
    CancellationDetailsRecord,
    CaseRecord,
    CustomerProfileRecord,
    DeliveryDetailsRecord,
    MerchantEvidenceRecord,
    PriorDisputeRecord,
    RefundHistoryEntry,
    RefundOrReversalRecord,
    SettlementRecord,
    TransactionRecord,
)

CASES: dict[str, CaseRecord] = {
    "CASE-1001": CaseRecord(
        case_id="CASE-1001",
        customer_id="CUST-3001",
        merchant_id="MERCH-4001",
        transaction_id="TXN-2001",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        status="open",
        opened_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
    ),
    "CASE-1002": CaseRecord(
        case_id="CASE-1002",
        customer_id="CUST-3002",
        merchant_id="MERCH-4001",
        transaction_id="TXN-2002",
        dispute_type=DisputeType.DUPLICATE_TRANSACTION,
        status="open",
        opened_at=datetime(2026, 6, 3, 14, 30, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
    ),
    "CASE-1003": CaseRecord(
        case_id="CASE-1003",
        customer_id="CUST-3003",
        merchant_id="MERCH-4002",
        transaction_id="TXN-2003",
        dispute_type=DisputeType.CANCELLED_SERVICE,
        status="open",
        opened_at=datetime(2026, 6, 5, 11, 15, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
    ),
}

TRANSACTIONS: dict[str, TransactionRecord] = {
    "TXN-2001": TransactionRecord(
        transaction_id="TXN-2001",
        case_id="CASE-1001",
        customer_id="CUST-3001",
        merchant_id="MERCH-4001",
        amount=Decimal("89.99"),
        currency="USD",
        posted_at=datetime(2026, 5, 28, 10, 5, tzinfo=UTC),
        description="Online purchase - Widget Pro",
    ),
    "TXN-2002": TransactionRecord(
        transaction_id="TXN-2002",
        case_id="CASE-1002",
        customer_id="CUST-3002",
        merchant_id="MERCH-4001",
        amount=Decimal("45.00"),
        currency="USD",
        posted_at=datetime(2026, 6, 1, 8, 40, tzinfo=UTC),
        description="Online purchase - Accessory Bundle",
    ),
    "TXN-2003": TransactionRecord(
        transaction_id="TXN-2003",
        case_id="CASE-1003",
        customer_id="CUST-3003",
        merchant_id="MERCH-4002",
        amount=Decimal("120.50"),
        currency="USD",
        posted_at=datetime(2026, 5, 20, 16, 0, tzinfo=UTC),
        description="Subscription service - Annual Plan",
    ),
}

AUTHORIZATIONS: dict[str, AuthorizationRecord] = {
    "TXN-2001": AuthorizationRecord(
        transaction_id="TXN-2001",
        authorization_code="AUTH-9001",
        authorized_at=datetime(2026, 5, 28, 10, 4, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
        approved=True,
    ),
    "TXN-2002": AuthorizationRecord(
        transaction_id="TXN-2002",
        authorization_code="AUTH-9002",
        authorized_at=datetime(2026, 6, 1, 8, 39, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
        approved=True,
    ),
    "TXN-2003": AuthorizationRecord(
        transaction_id="TXN-2003",
        authorization_code="AUTH-9003",
        authorized_at=datetime(2026, 5, 20, 15, 59, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
        approved=True,
    ),
}

SETTLEMENTS: dict[str, SettlementRecord] = {
    "TXN-2001": SettlementRecord(
        transaction_id="TXN-2001",
        settlement_id="SETL-8001",
        settled_at=datetime(2026, 5, 29, 2, 0, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
    ),
    "TXN-2002": SettlementRecord(
        transaction_id="TXN-2002",
        settlement_id="SETL-8002",
        settled_at=datetime(2026, 6, 2, 2, 0, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
    ),
    "TXN-2003": SettlementRecord(
        transaction_id="TXN-2003",
        settlement_id="SETL-8003",
        settled_at=datetime(2026, 5, 21, 2, 0, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
    ),
}

REFUNDS_OR_REVERSALS: dict[str, tuple[RefundOrReversalRecord, ...]] = {
    "TXN-2001": (),
    "TXN-2002": (
        RefundOrReversalRecord(
            transaction_id="TXN-2002",
            refund_id="REFUND-7001",
            refunded_at=datetime(2026, 6, 4, 9, 0, tzinfo=UTC),
            amount=Decimal("45.00"),
            currency="USD",
            reason="Duplicate charge reversed by merchant",
        ),
    ),
    "TXN-2003": (),
}

CUSTOMER_PROFILES: dict[str, CustomerProfileRecord] = {
    "CUST-3001": CustomerProfileRecord(
        customer_id="CUST-3001",
        display_name="Jane Doe",
        email="jane.doe@example.com",
        customer_since=datetime(2022, 3, 1, tzinfo=UTC),
        tenure_days=1584,
    ),
    "CUST-3002": CustomerProfileRecord(
        customer_id="CUST-3002",
        display_name="John Smith",
        email="john.smith@example.com",
        customer_since=datetime(2023, 7, 15, tzinfo=UTC),
        tenure_days=1082,
    ),
    "CUST-3003": CustomerProfileRecord(
        customer_id="CUST-3003",
        display_name="Amara Chen",
        email="amara.chen@example.com",
        customer_since=datetime(2020, 11, 20, tzinfo=UTC),
        tenure_days=1979,
    ),
}

PRIOR_DISPUTES: dict[str, tuple[PriorDisputeRecord, ...]] = {
    "CUST-3001": (
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5001",
            customer_id="CUST-3001",
            case_id="CASE-0501",
            dispute_type=DisputeType.MERCHANT_ERROR,
            outcome="reject_chargeback",
            resolved_at=datetime(2025, 9, 10, tzinfo=UTC),
        ),
    ),
    "CUST-3002": (),
    "CUST-3003": (
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5002",
            customer_id="CUST-3003",
            case_id="CASE-0502",
            dispute_type=DisputeType.CARD_NOT_PRESENT_FRAUD,
            outcome="accept_chargeback",
            resolved_at=datetime(2024, 12, 2, tzinfo=UTC),
        ),
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5003",
            customer_id="CUST-3003",
            case_id="CASE-0503",
            dispute_type=DisputeType.GOODS_NOT_RECEIVED,
            outcome="request_more_evidence",
            resolved_at=datetime(2025, 3, 18, tzinfo=UTC),
        ),
    ),
}

REFUND_HISTORY: dict[str, tuple[RefundHistoryEntry, ...]] = {
    "CUST-3001": (
        RefundHistoryEntry(
            refund_id="REFUNDHIST-6001",
            customer_id="CUST-3001",
            transaction_id="TXN-1501",
            amount=Decimal("15.00"),
            currency="USD",
            refunded_at=datetime(2025, 11, 1, tzinfo=UTC),
        ),
    ),
    "CUST-3002": (),
    "CUST-3003": (
        RefundHistoryEntry(
            refund_id="REFUNDHIST-6002",
            customer_id="CUST-3003",
            transaction_id="TXN-1502",
            amount=Decimal("30.00"),
            currency="USD",
            refunded_at=datetime(2025, 4, 22, tzinfo=UTC),
        ),
    ),
}

MERCHANT_EVIDENCE: dict[str, MerchantEvidenceRecord] = {
    "CASE-1001": MerchantEvidenceRecord(
        case_id="CASE-1001",
        merchant_id="MERCH-4001",
        acknowledgement=False,
        evidence_summary="Merchant has not responded to the evidence request.",
        submitted_at=datetime(2026, 6, 2, tzinfo=UTC),
    ),
    "CASE-1002": MerchantEvidenceRecord(
        case_id="CASE-1002",
        merchant_id="MERCH-4001",
        acknowledgement=True,
        evidence_summary="Merchant confirms the duplicate charge and has reversed it.",
        submitted_at=datetime(2026, 6, 4, tzinfo=UTC),
    ),
    "CASE-1003": MerchantEvidenceRecord(
        case_id="CASE-1003",
        merchant_id="MERCH-4002",
        acknowledgement=True,
        evidence_summary="Merchant acknowledges the cancellation request but has not yet uploaded confirmation.",
        submitted_at=datetime(2026, 6, 6, tzinfo=UTC),
    ),
}

DELIVERY_DETAILS: dict[str, DeliveryDetailsRecord] = {
    "CASE-1001": DeliveryDetailsRecord(
        case_id="CASE-1001",
        delivered=False,
        delivery_date=None,
        carrier=None,
        tracking_number=None,
    ),
    "CASE-1002": DeliveryDetailsRecord(
        case_id="CASE-1002",
        delivered=True,
        delivery_date=datetime(2026, 6, 1, 18, 0, tzinfo=UTC),
        carrier="ParcelSwift",
        tracking_number="PS-773311",
    ),
    "CASE-1003": DeliveryDetailsRecord(
        case_id="CASE-1003",
        delivered=True,
        delivery_date=datetime(2026, 5, 20, 16, 30, tzinfo=UTC),
        carrier=None,
        tracking_number=None,
    ),
}

CANCELLATION_DETAILS: dict[str, CancellationDetailsRecord] = {
    "CASE-1001": CancellationDetailsRecord(
        case_id="CASE-1001",
        cancelled=False,
        cancellation_date=None,
        confirmation_reference=None,
    ),
    "CASE-1002": CancellationDetailsRecord(
        case_id="CASE-1002",
        cancelled=False,
        cancellation_date=None,
        confirmation_reference=None,
    ),
    "CASE-1003": CancellationDetailsRecord(
        case_id="CASE-1003",
        cancelled=True,
        cancellation_date=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        confirmation_reference="CANCEL-CONF-7788",
    ),
}
```

- [ ] **Step 2: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/seed_data.py
git commit -m "feat: add deterministic cross-referenced seed data"
```

---

### Task 4: `repository.py` + seed-data consistency tests

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/repository.py`
- Create: `dispute-mcp-server/tests/test_seed_data_consistency.py`

**Interfaces:**
- Consumes: everything from `seed_data.py` and `models.py`.
- Produces: `NotFoundError`, `DisputeRepository` — consumed by every `tools/*_tools.py` module and `main.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/repository.py`**

```python
"""Repository layer: owns seeded data behind typed lookup methods.

No business decisions happen here — only reads, and the two narrow
mutations (case status, audit log) that update_case/write_audit need.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from dispute_mcp_server import seed_data
from dispute_mcp_server.models import (
    AuditRecord,
    AuthorizationRecord,
    CancellationDetailsRecord,
    CaseRecord,
    CustomerProfileRecord,
    DeliveryDetailsRecord,
    MerchantEvidenceRecord,
    PriorDisputeRecord,
    RefundHistoryEntry,
    RefundOrReversalRecord,
    SettlementRecord,
    TransactionRecord,
)


class NotFoundError(Exception):
    """Raised when a requested identifier has no seeded record."""


class DisputeRepository:
    """In-memory repository over the seeded mock data.

    Mutations (update_case_status, append_audit_record) only affect this
    process's in-memory copy — no persistence across restarts, since
    nothing in this prompt requires it.
    """

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = dict(seed_data.CASES)
        self._audit_log: list[AuditRecord] = []

    def get_case(self, case_id: str) -> CaseRecord:
        try:
            return self._cases[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def update_case_status(self, case_id: str, new_status: str) -> CaseRecord:
        current = self.get_case(case_id)
        updated = current.model_copy(update={"status": new_status})
        self._cases[case_id] = updated
        return updated

    def append_audit_record(
        self, case_id: str, event_description: str, idempotency_key: str
    ) -> AuditRecord:
        if case_id not in self._cases:
            raise NotFoundError(f"case not found: {case_id}")
        record = AuditRecord(
            audit_id=f"AUDIT-{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            event_description=event_description,
            recorded_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )
        self._audit_log.append(record)
        return record

    def get_transaction(self, transaction_id: str) -> TransactionRecord:
        try:
            return seed_data.TRANSACTIONS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_authorization(self, transaction_id: str) -> AuthorizationRecord:
        try:
            return seed_data.AUTHORIZATIONS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_settlement(self, transaction_id: str) -> SettlementRecord:
        try:
            return seed_data.SETTLEMENTS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_refunds_or_reversals(
        self, transaction_id: str
    ) -> tuple[RefundOrReversalRecord, ...]:
        try:
            return seed_data.REFUNDS_OR_REVERSALS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_customer_profile(self, customer_id: str) -> CustomerProfileRecord:
        try:
            return seed_data.CUSTOMER_PROFILES[customer_id]
        except KeyError:
            raise NotFoundError(f"customer not found: {customer_id}") from None

    def get_prior_disputes(self, customer_id: str) -> tuple[PriorDisputeRecord, ...]:
        if customer_id not in seed_data.CUSTOMER_PROFILES:
            raise NotFoundError(f"customer not found: {customer_id}")
        return seed_data.PRIOR_DISPUTES.get(customer_id, ())

    def get_refund_history(self, customer_id: str) -> tuple[RefundHistoryEntry, ...]:
        if customer_id not in seed_data.CUSTOMER_PROFILES:
            raise NotFoundError(f"customer not found: {customer_id}")
        return seed_data.REFUND_HISTORY.get(customer_id, ())

    def get_merchant_evidence(self, case_id: str) -> MerchantEvidenceRecord:
        try:
            return seed_data.MERCHANT_EVIDENCE[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def get_delivery_details(self, case_id: str) -> DeliveryDetailsRecord:
        try:
            return seed_data.DELIVERY_DETAILS[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def get_cancellation_details(self, case_id: str) -> CancellationDetailsRecord:
        try:
            return seed_data.CANCELLATION_DETAILS[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_seed_data_consistency.py`**

```python
"""Cross-reference integrity checks for the seeded mock data."""

from dispute_mcp_server import seed_data


def test_every_case_transaction_id_has_a_transaction_record() -> None:
    for case in seed_data.CASES.values():
        assert case.transaction_id in seed_data.TRANSACTIONS


def test_every_transaction_case_id_matches_a_real_case() -> None:
    for transaction in seed_data.TRANSACTIONS.values():
        assert transaction.case_id in seed_data.CASES


def test_every_transaction_has_authorization_and_settlement() -> None:
    for transaction_id in seed_data.TRANSACTIONS:
        assert transaction_id in seed_data.AUTHORIZATIONS
        assert transaction_id in seed_data.SETTLEMENTS
        assert transaction_id in seed_data.REFUNDS_OR_REVERSALS


def test_every_case_customer_id_has_a_customer_profile() -> None:
    for case in seed_data.CASES.values():
        assert case.customer_id in seed_data.CUSTOMER_PROFILES


def test_every_customer_has_prior_disputes_and_refund_history_entries() -> None:
    for customer_id in seed_data.CUSTOMER_PROFILES:
        assert customer_id in seed_data.PRIOR_DISPUTES
        assert customer_id in seed_data.REFUND_HISTORY


def test_every_case_has_merchant_evidence_delivery_and_cancellation_details() -> None:
    for case_id in seed_data.CASES:
        assert case_id in seed_data.MERCHANT_EVIDENCE
        assert case_id in seed_data.DELIVERY_DETAILS
        assert case_id in seed_data.CANCELLATION_DETAILS


def test_transaction_amounts_match_their_case_amounts() -> None:
    for case in seed_data.CASES.values():
        transaction = seed_data.TRANSACTIONS[case.transaction_id]
        assert transaction.amount == case.amount
        assert transaction.currency == case.currency


def test_authorization_and_settlement_amounts_match_transaction_amounts() -> None:
    for transaction_id, transaction in seed_data.TRANSACTIONS.items():
        auth = seed_data.AUTHORIZATIONS[transaction_id]
        settlement = seed_data.SETTLEMENTS[transaction_id]
        assert auth.amount == transaction.amount
        assert settlement.amount == transaction.amount
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_seed_data_consistency.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/repository.py dispute-mcp-server/tests/test_seed_data_consistency.py
git commit -m "feat: add repository layer with seed-data consistency tests"
```

---

### Task 5: `config.py` + `logging.py` + logging tests

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/config.py`
- Create: `dispute-mcp-server/src/dispute_mcp_server/logging.py`
- Create: `dispute-mcp-server/tests/test_logging.py`

**Interfaces:**
- Produces: `Settings`, `load_settings()`, `configure_logging()`, `log_tool_call()` — consumed by `main.py` and every `tools/*_tools.py` module.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/config.py`**

```python
"""Environment-backed settings for dispute-mcp-server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("MCP_SERVICE_NAME", "dispute-mcp-server"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 2: Write `dispute-mcp-server/src/dispute_mcp_server/logging.py`**

```python
"""Structured logging for MCP tool calls.

Logs only the tool name, one relevant identifier, success/failure, and
duration — never full record contents, free-text comments, or raw
exception bodies.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

_LOGGER_NAME = "dispute_mcp_server"


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def log_tool_call(
    logger: logging.Logger, tool_name: str, id_from: Callable[..., str | None]
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Wrap a tool function, logging its outcome without its full payload."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            record_id = id_from(*args, **kwargs)
            started = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = (time.monotonic() - started) * 1000
                logger.warning(
                    "tool=%s id=%s outcome=failure duration_ms=%.2f error=%s",
                    tool_name,
                    record_id,
                    duration_ms,
                    type(exc).__name__,
                )
                raise
            duration_ms = (time.monotonic() - started) * 1000
            logger.info(
                "tool=%s id=%s outcome=success duration_ms=%.2f",
                tool_name,
                record_id,
                duration_ms,
            )
            return result

        return wrapper

    return decorator
```

- [ ] **Step 3: Write `dispute-mcp-server/tests/test_logging.py`**

```python
"""Tests for dispute_mcp_server.logging's log_tool_call wrapper."""

import logging

import pytest

from dispute_mcp_server.logging import configure_logging, log_tool_call


def test_configure_logging_returns_a_named_logger() -> None:
    logger = configure_logging("INFO")
    assert logger.name == "dispute_mcp_server"
    assert logger.level == logging.INFO


def test_log_tool_call_logs_success_with_id_and_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = configure_logging("INFO")

    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> str:
        return f"found {case_id}"

    with caplog.at_level(logging.INFO, logger="dispute_mcp_server"):
        result = get_case("CASE-1001")

    assert result == "found CASE-1001"
    assert any(
        "tool=get_case" in r.message and "id=CASE-1001" in r.message and "outcome=success" in r.message
        for r in caplog.records
    )


def test_log_tool_call_logs_failure_without_leaking_exception_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = configure_logging("INFO")

    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> str:
        raise ValueError("some sensitive internal detail")

    with caplog.at_level(logging.INFO, logger="dispute_mcp_server"):
        with pytest.raises(ValueError, match="some sensitive internal detail"):
            get_case("CASE-NOPE")

    failure_logs = [r for r in caplog.records if "outcome=failure" in r.message]
    assert len(failure_logs) == 1
    assert "tool=get_case" in failure_logs[0].message
    assert "id=CASE-NOPE" in failure_logs[0].message
    assert "ValueError" in failure_logs[0].message
    assert "some sensitive internal detail" not in failure_logs[0].message
```

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_logging.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/config.py dispute-mcp-server/src/dispute_mcp_server/logging.py dispute-mcp-server/tests/test_logging.py
git commit -m "feat: add config and structured tool-call logging"
```

---

### Task 6: `tools/case_tools.py` — get_case, update_case, write_audit

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/tools/__init__.py` (empty)
- Create: `dispute-mcp-server/src/dispute_mcp_server/tools/case_tools.py`
- Create: `dispute-mcp-server/tests/test_case_tools.py`

**Interfaces:**
- Consumes: `DisputeRepository`, `NotFoundError` from `repository.py`; `CaseRecord` from `models.py`; `log_tool_call` from `logging.py`; `UpdateCaseStatusRequest`, `CreateAuditEntryRequest`, `McpWriteResponse`, `McpStatus`, `McpErrorInfo` from `chargeback_contracts.mcp`.
- Produces: `register_case_tools(mcp, repository, logger)` — called by `main.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/tools/case_tools.py`**

```python
"""Case tool group: get_case, update_case, write_audit."""

from __future__ import annotations

import logging

from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    McpErrorInfo,
    McpStatus,
    McpWriteResponse,
    UpdateCaseStatusRequest,
)
from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import CaseRecord
from dispute_mcp_server.repository import DisputeRepository, NotFoundError


def register_case_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> CaseRecord:
        """Get a chargeback case by ID."""
        return repository.get_case(case_id)

    @mcp.tool
    @log_tool_call(logger, "update_case", id_from=lambda request: request.case_id)
    def update_case(request: UpdateCaseStatusRequest) -> McpWriteResponse:
        """Update a case's status. Requires a non-blank idempotency key."""
        try:
            repository.update_case_status(request.case_id, request.new_status)
        except NotFoundError:
            return McpWriteResponse(
                status=McpStatus.FAILURE,
                audit_correlation_id=request.idempotency_key,
                error=McpErrorInfo(
                    error_code="case_not_found",
                    safe_message="No case exists with the given case_id.",
                ),
            )
        return McpWriteResponse(
            status=McpStatus.SUCCESS,
            audit_correlation_id=request.idempotency_key,
        )

    @mcp.tool
    @log_tool_call(logger, "write_audit", id_from=lambda request: request.case_id)
    def write_audit(request: CreateAuditEntryRequest) -> McpWriteResponse:
        """Append an audit log entry for a case. Requires a non-blank idempotency key."""
        try:
            audit_record = repository.append_audit_record(
                request.case_id, request.event_description, request.idempotency_key
            )
        except NotFoundError:
            return McpWriteResponse(
                status=McpStatus.FAILURE,
                audit_correlation_id=request.idempotency_key,
                error=McpErrorInfo(
                    error_code="case_not_found",
                    safe_message="No case exists with the given case_id.",
                ),
            )
        return McpWriteResponse(
            status=McpStatus.SUCCESS,
            audit_correlation_id=audit_record.audit_id,
        )
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_case_tools.py`**

```python
"""Tests for the case tool group, via an in-memory fastmcp.Client."""

import pytest
from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    McpStatus,
    UpdateCaseStatusRequest,
)
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.case_tools import register_case_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-case-tools")
    register_case_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_case_returns_seeded_case(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_case", {"case_id": "CASE-1001"})
    assert result.data["case_id"] == "CASE-1001"
    assert result.data["customer_id"] == "CUST-3001"


async def test_get_case_unknown_id_raises_tool_error(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_case", {"case_id": "CASE-NOPE"})


async def test_update_case_succeeds_and_persists_within_process(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "update_case",
            {
                "request": UpdateCaseStatusRequest(
                    case_id="CASE-1001",
                    idempotency_key="idem-1",
                    new_status="closed",
                ).model_dump(mode="json")
            },
        )
        assert response.data["status"] == McpStatus.SUCCESS.value

        updated = await client.call_tool("get_case", {"case_id": "CASE-1001"})
        assert updated.data["status"] == "closed"


async def test_update_case_unknown_id_returns_failure_not_exception(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "update_case",
            {
                "request": UpdateCaseStatusRequest(
                    case_id="CASE-NOPE",
                    idempotency_key="idem-2",
                    new_status="closed",
                ).model_dump(mode="json")
            },
        )
    assert response.data["status"] == McpStatus.FAILURE.value
    assert response.data["error"]["error_code"] == "case_not_found"


async def test_write_audit_succeeds(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "write_audit",
            {
                "request": CreateAuditEntryRequest(
                    case_id="CASE-1002",
                    idempotency_key="idem-3",
                    event_description="Investigator reviewed merchant evidence.",
                ).model_dump(mode="json")
            },
        )
    assert response.data["status"] == McpStatus.SUCCESS.value


async def test_write_audit_unknown_case_returns_failure(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "write_audit",
            {
                "request": CreateAuditEntryRequest(
                    case_id="CASE-NOPE",
                    idempotency_key="idem-4",
                    event_description="x",
                ).model_dump(mode="json")
            },
        )
    assert response.data["status"] == McpStatus.FAILURE.value
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_case_tools.py -v`
Expected: all tests pass. If `fastmcp.Client.call_tool` doesn't accept a nested Pydantic-model-shaped dict the way shown above (verify against the real installed `fastmcp==3.4.4` behavior — the plan's brief for this task should have you actually run this against the real package rather than trust this template blindly), adjust the exact call shape based on the real error, and note the adjustment in your report.

- [ ] **Step 4: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/tools/__init__.py dispute-mcp-server/src/dispute_mcp_server/tools/case_tools.py dispute-mcp-server/tests/test_case_tools.py
git commit -m "feat: add case tool group (get_case, update_case, write_audit)"
```

---

### Task 7: `tools/transaction_tools.py`

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/tools/transaction_tools.py`
- Create: `dispute-mcp-server/tests/test_transaction_tools.py`

**Interfaces:**
- Consumes: `DisputeRepository`, `NotFoundError`, `log_tool_call`, models from `models.py`.
- Produces: `register_transaction_tools(mcp, repository, logger)` — called by `main.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/tools/transaction_tools.py`**

```python
"""Transaction tool group: get_transaction, get_authorization, get_settlement,
get_refund_or_reversal."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    AuthorizationRecord,
    RefundOrReversalRecord,
    SettlementRecord,
    TransactionRecord,
)
from dispute_mcp_server.repository import DisputeRepository


def register_transaction_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_transaction", id_from=lambda transaction_id: transaction_id)
    def get_transaction(transaction_id: str) -> TransactionRecord:
        """Get a transaction by ID."""
        return repository.get_transaction(transaction_id)

    @mcp.tool
    @log_tool_call(logger, "get_authorization", id_from=lambda transaction_id: transaction_id)
    def get_authorization(transaction_id: str) -> AuthorizationRecord:
        """Get the authorization for a transaction."""
        return repository.get_authorization(transaction_id)

    @mcp.tool
    @log_tool_call(logger, "get_settlement", id_from=lambda transaction_id: transaction_id)
    def get_settlement(transaction_id: str) -> SettlementRecord:
        """Get the settlement for a transaction."""
        return repository.get_settlement(transaction_id)

    @mcp.tool
    @log_tool_call(
        logger, "get_refund_or_reversal", id_from=lambda transaction_id: transaction_id
    )
    def get_refund_or_reversal(transaction_id: str) -> tuple[RefundOrReversalRecord, ...]:
        """Get any refunds or reversals for a transaction (may be empty)."""
        return repository.get_refunds_or_reversals(transaction_id)
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_transaction_tools.py`**

```python
"""Tests for the transaction tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.transaction_tools import register_transaction_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-transaction-tools")
    register_transaction_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_transaction_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_transaction", {"transaction_id": "TXN-2001"})
    assert result.data["transaction_id"] == "TXN-2001"
    assert result.data["case_id"] == "CASE-1001"


async def test_get_transaction_unknown_id_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_transaction", {"transaction_id": "TXN-NOPE"})


async def test_get_authorization_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_authorization", {"transaction_id": "TXN-2001"})
    assert result.data["authorization_code"] == "AUTH-9001"
    assert result.data["approved"] is True


async def test_get_settlement_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_settlement", {"transaction_id": "TXN-2002"})
    assert result.data["settlement_id"] == "SETL-8002"


async def test_get_refund_or_reversal_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_refund_or_reversal", {"transaction_id": "TXN-2002"}
        )
    assert len(result.data) == 1
    assert result.data[0]["refund_id"] == "REFUND-7001"


async def test_get_refund_or_reversal_returns_empty_list_when_none(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_refund_or_reversal", {"transaction_id": "TXN-2001"}
        )
    assert result.data == []


async def test_get_refund_or_reversal_unknown_transaction_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_refund_or_reversal", {"transaction_id": "TXN-NOPE"})
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_transaction_tools.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/tools/transaction_tools.py dispute-mcp-server/tests/test_transaction_tools.py
git commit -m "feat: add transaction tool group"
```

---

### Task 8: `tools/customer_tools.py`

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/tools/customer_tools.py`
- Create: `dispute-mcp-server/tests/test_customer_tools.py`

**Interfaces:**
- Consumes: `DisputeRepository`, `NotFoundError`, `log_tool_call`, models from `models.py`.
- Produces: `register_customer_tools(mcp, repository, logger)` — called by `main.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/tools/customer_tools.py`**

```python
"""Customer tool group: get_customer_profile, get_prior_disputes,
get_refund_history."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    CustomerProfileRecord,
    PriorDisputeRecord,
    RefundHistoryEntry,
)
from dispute_mcp_server.repository import DisputeRepository


def register_customer_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_customer_profile", id_from=lambda customer_id: customer_id)
    def get_customer_profile(customer_id: str) -> CustomerProfileRecord:
        """Get a customer profile by ID."""
        return repository.get_customer_profile(customer_id)

    @mcp.tool
    @log_tool_call(logger, "get_prior_disputes", id_from=lambda customer_id: customer_id)
    def get_prior_disputes(customer_id: str) -> tuple[PriorDisputeRecord, ...]:
        """Get a customer's prior dispute history (may be empty)."""
        return repository.get_prior_disputes(customer_id)

    @mcp.tool
    @log_tool_call(logger, "get_refund_history", id_from=lambda customer_id: customer_id)
    def get_refund_history(customer_id: str) -> tuple[RefundHistoryEntry, ...]:
        """Get a customer's refund history (may be empty)."""
        return repository.get_refund_history(customer_id)
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_customer_tools.py`**

```python
"""Tests for the customer tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.customer_tools import register_customer_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-customer-tools")
    register_customer_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_customer_profile_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_customer_profile", {"customer_id": "CUST-3001"})
    assert result.data["display_name"] == "Jane Doe"


async def test_get_customer_profile_unknown_id_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_customer_profile", {"customer_id": "CUST-NOPE"})


async def test_get_prior_disputes_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_prior_disputes", {"customer_id": "CUST-3003"})
    assert len(result.data) == 2


async def test_get_prior_disputes_returns_empty_list_when_none(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_prior_disputes", {"customer_id": "CUST-3002"})
    assert result.data == []


async def test_get_refund_history_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_refund_history", {"customer_id": "CUST-3001"})
    assert len(result.data) == 1


async def test_get_refund_history_unknown_customer_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_refund_history", {"customer_id": "CUST-NOPE"})
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_customer_tools.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/tools/customer_tools.py dispute-mcp-server/tests/test_customer_tools.py
git commit -m "feat: add customer tool group"
```

---

### Task 9: `tools/merchant_tools.py`

**Files:**
- Create: `dispute-mcp-server/src/dispute_mcp_server/tools/merchant_tools.py`
- Create: `dispute-mcp-server/tests/test_merchant_tools.py`

**Interfaces:**
- Consumes: `DisputeRepository`, `NotFoundError`, `log_tool_call`, models from `models.py`.
- Produces: `register_merchant_tools(mcp, repository, logger)` — called by `main.py`.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/tools/merchant_tools.py`**

```python
"""Merchant tool group: get_merchant_evidence, get_delivery_details,
get_cancellation_details."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    CancellationDetailsRecord,
    DeliveryDetailsRecord,
    MerchantEvidenceRecord,
)
from dispute_mcp_server.repository import DisputeRepository


def register_merchant_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_merchant_evidence", id_from=lambda case_id: case_id)
    def get_merchant_evidence(case_id: str) -> MerchantEvidenceRecord:
        """Get the merchant's submitted evidence for a case."""
        return repository.get_merchant_evidence(case_id)

    @mcp.tool
    @log_tool_call(logger, "get_delivery_details", id_from=lambda case_id: case_id)
    def get_delivery_details(case_id: str) -> DeliveryDetailsRecord:
        """Get delivery details for a case."""
        return repository.get_delivery_details(case_id)

    @mcp.tool
    @log_tool_call(logger, "get_cancellation_details", id_from=lambda case_id: case_id)
    def get_cancellation_details(case_id: str) -> CancellationDetailsRecord:
        """Get cancellation details for a case."""
        return repository.get_cancellation_details(case_id)
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_merchant_tools.py`**

```python
"""Tests for the merchant tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.merchant_tools import register_merchant_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-merchant-tools")
    register_merchant_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_merchant_evidence_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_merchant_evidence", {"case_id": "CASE-1002"})
    assert result.data["acknowledgement"] is True


async def test_get_merchant_evidence_unknown_case_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_merchant_evidence", {"case_id": "CASE-NOPE"})


async def test_get_delivery_details_reflects_non_delivery(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_delivery_details", {"case_id": "CASE-1001"})
    assert result.data["delivered"] is False


async def test_get_delivery_details_reflects_delivery(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_delivery_details", {"case_id": "CASE-1002"})
    assert result.data["delivered"] is True
    assert result.data["tracking_number"] == "PS-773311"


async def test_get_cancellation_details_reflects_cancellation(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_cancellation_details", {"case_id": "CASE-1003"})
    assert result.data["cancelled"] is True
    assert result.data["confirmation_reference"] == "CANCEL-CONF-7788"


async def test_get_cancellation_details_unknown_case_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_cancellation_details", {"case_id": "CASE-NOPE"})
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_merchant_tools.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/tools/merchant_tools.py dispute-mcp-server/tests/test_merchant_tools.py
git commit -m "feat: add merchant tool group"
```

---

### Task 10: `main.py` + server startup / tool discovery tests

**Files:**
- Modify: `dispute-mcp-server/src/dispute_mcp_server/main.py` (create if absent)
- Create: `dispute-mcp-server/tests/test_server_startup.py`

**Interfaces:**
- Consumes: everything from Tasks 2-9.
- Produces: the module-level `mcp` app object, which is what Docker/Makefile targets run.

- [ ] **Step 1: Write `dispute-mcp-server/src/dispute_mcp_server/main.py`**

```python
"""Entrypoint: builds the FastMCP app and registers all tool groups."""

from __future__ import annotations

from fastmcp import FastMCP

from dispute_mcp_server.config import load_settings
from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.case_tools import register_case_tools
from dispute_mcp_server.tools.customer_tools import register_customer_tools
from dispute_mcp_server.tools.merchant_tools import register_merchant_tools
from dispute_mcp_server.tools.transaction_tools import register_transaction_tools


def create_app() -> FastMCP:
    settings = load_settings()
    logger = configure_logging(settings.log_level)
    repository = DisputeRepository()

    mcp = FastMCP(settings.service_name)
    register_case_tools(mcp, repository, logger)
    register_transaction_tools(mcp, repository, logger)
    register_customer_tools(mcp, repository, logger)
    register_merchant_tools(mcp, repository, logger)
    return mcp


mcp = create_app()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Write `dispute-mcp-server/tests/test_server_startup.py`**

```python
"""Server startup and tool discovery tests."""

from fastmcp import Client

from dispute_mcp_server.main import create_app

EXPECTED_TOOL_NAMES = {
    "get_case",
    "update_case",
    "write_audit",
    "get_transaction",
    "get_authorization",
    "get_settlement",
    "get_refund_or_reversal",
    "get_customer_profile",
    "get_prior_disputes",
    "get_refund_history",
    "get_merchant_evidence",
    "get_delivery_details",
    "get_cancellation_details",
}


async def test_app_starts_and_exposes_exactly_thirteen_tools() -> None:
    app = create_app()
    async with Client(app) as client:
        tools = await client.list_tools()
    tool_names = {tool.name for tool in tools}
    assert tool_names == EXPECTED_TOOL_NAMES
    assert len(EXPECTED_TOOL_NAMES) == 13


async def test_creating_the_app_twice_does_not_error() -> None:
    # Confirms tool registration has no hidden global/shared state that
    # breaks on a second instantiation (e.g. two test runs in one process).
    first = create_app()
    second = create_app()
    async with Client(first) as client:
        first_tools = {t.name for t in await client.list_tools()}
    async with Client(second) as client:
        second_tools = {t.name for t in await client.list_tools()}
    assert first_tools == second_tools == EXPECTED_TOOL_NAMES
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest dispute-mcp-server/tests/test_server_startup.py -v`
Expected: all tests pass.

- [ ] **Step 4: Run the full dispute-mcp-server suite**

Run: `uv run pytest dispute-mcp-server/ -v`
Expected: every test file created in Tasks 3-10 passes.

- [ ] **Step 5: Commit**

```bash
git add dispute-mcp-server/src/dispute_mcp_server/main.py dispute-mcp-server/tests/test_server_startup.py
git commit -m "feat: wire main.py entrypoint and add server startup/discovery tests"
```

---

### Task 11: Remove the Prompt-1 smoke test; verify mypy/ruff

**Files:**
- Delete: `dispute-mcp-server/tests/test_import.py`
- Modify: root `pyproject.toml` (`[tool.mypy] exclude` — remove the `dispute-mcp-server` line, since it now has real tests)

**Interfaces:** none new.

- [ ] **Step 1: Delete the old smoke test**

```bash
git rm dispute-mcp-server/tests/test_import.py
```

- [ ] **Step 2: Remove `dispute-mcp-server` from the mypy exclude list**

Find the `[tool.mypy]` `exclude` list in root `pyproject.toml` (narrowed in Prompt 2 to name 9 packages without real tests). Remove the `"^dispute-mcp-server/tests/",` line — this package now has real tests and should be strict-mypy-checked like `contracts`.

- [ ] **Step 3: Run mypy**

Run: `uv run mypy .`
Expected: clean, including `dispute-mcp-server/src` and `dispute-mcp-server/tests` now. Fix any real error in the specific file it points to — do not weaken `strict = true`.

- [ ] **Step 4: Run ruff**

Run: `uv run ruff check .` and `uv run ruff format --check .`
Expected: clean (use `enum.StrEnum` conventions if any enum is added, `datetime.UTC`, sorted imports, lines under 100 columns — matching the rest of the workspace).

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest`
Expected: all tests across all packages pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml dispute-mcp-server/tests/test_import.py
git commit -m "chore: remove dispute-mcp-server Prompt-1 smoke test, strict-check it in mypy"
```

(`git rm` already stages the deletion; `git add` on a deleted path is a no-op safety net — adjust if your git version needs `git add -u` instead.)

---

### Task 12: Docker Compose — runnable `dispute-mcp-server` service

**Files:**
- Modify: `docker-compose.yml`

**Interfaces:** none.

- [ ] **Step 1: Replace the comments-only scaffold**

Current content (from Prompt 1):
```yaml
# Foundation-stage scaffold only.
#
# Full service orchestration (agents, agent-registry, dispute-mcp-server,
# ChromaDB, investigator-ui) is completed in Prompt 12.
#
# Ollama is intentionally NOT defined here: it runs natively on the Docker
# host, not as a container. Services that need it reach it via
# OLLAMA_BASE_URL (see .env.example), typically
# http://host.docker.internal:11434.
#
# No services are defined yet — adding them prematurely would misrepresent
# functionality that doesn't exist in this prompt.

services: {}
```

Replace with:
```yaml
# Full service orchestration (agents, agent-registry, ChromaDB,
# investigator-ui) is completed in Prompt 12. Only dispute-mcp-server is
# defined here — this prompt's scope.
#
# Ollama is intentionally NOT defined here: it runs natively on the Docker
# host, not as a container. Services that need it reach it via
# OLLAMA_BASE_URL (see .env.example), typically
# http://host.docker.internal:11434.
#
# dispute-mcp-server communicates over MCP's stdio transport (confirmed
# via fastmcp's Client API during design research) rather than an HTTP
# port, so no port mapping is declared — the prompt that adds the
# Orchestrator/specialists will define how they invoke this container.

services:
  dispute-mcp-server:
    build:
      context: .
      dockerfile: dispute-mcp-server/Dockerfile
    image: agentic-chargeback-investigator/dispute-mcp-server:local
    environment:
      MCP_SERVICE_NAME: dispute-mcp-server
      LOG_LEVEL: INFO
    stdin_open: true
    tty: true
```

- [ ] **Step 2: Write `dispute-mcp-server/Dockerfile`**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY contracts/ contracts/
COPY dispute-mcp-server/ dispute-mcp-server/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --package dispute-mcp-server

CMD ["uv", "run", "--package", "dispute-mcp-server", "python", "-m", "dispute_mcp_server.main"]
```

- [ ] **Step 3: Statically validate Compose syntax**

Run: `docker compose config` (if the `docker` CLI is available in this environment) to confirm the YAML parses and resolves correctly.
Expected: valid config printed, no errors. If the `docker` CLI/daemon isn't usable in this environment (as was the case in Prompt 1 — no reachable daemon), record that limitation explicitly in your report rather than claiming a container build/run was tested. Do not claim a container test ran if it didn't.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml dispute-mcp-server/Dockerfile
git commit -m "feat: add runnable dispute-mcp-server Docker Compose service"
```

---

### Task 13: Makefile targets

**Files:**
- Modify: `Makefile`

**Interfaces:** none.

- [ ] **Step 1: Add two targets**

Add to the `Makefile` (after the existing `test` target, before `verify`):

```makefile
mcp-test:
	uv run pytest dispute-mcp-server/tests -v

mcp-run:
	uv run --package dispute-mcp-server python -m dispute_mcp_server.main
```

Add `mcp-test mcp-run` to the `.PHONY` line at the top alongside the existing targets.

- [ ] **Step 2: Verify existing targets still work**

Run: `make test` (existing target, should be unaffected) and `make mcp-test` (new target).
Expected: both pass.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add mcp-test and mcp-run Makefile targets"
```

---

### Task 14: README — Dispute MCP Server section

**Files:**
- Modify: `README.md`

**Interfaces:** none.

- [ ] **Step 1: Insert a new section after "Shared contract layer"**

```markdown
## Dispute MCP Server

`dispute-mcp-server` is a single FastMCP server exposing mocked enterprise
data through four tool groups — case, transaction, customer, merchant (13
tools total). All responses come from deterministic, cross-referenced
seed data (`seed_data.py`); there are no live integrations and no business
decisions made here.

Tool groups:

- **Case**: `get_case`, `update_case`, `write_audit`
- **Transaction**: `get_transaction`, `get_authorization`, `get_settlement`, `get_refund_or_reversal`
- **Customer**: `get_customer_profile`, `get_prior_disputes`, `get_refund_history`
- **Merchant**: `get_merchant_evidence`, `get_delivery_details`, `get_cancellation_details`

`update_case` and `write_audit` reuse the shared `chargeback_contracts.mcp`
write-side envelope contracts (idempotency key required, structured
success/failure response); every other tool returns a package-owned
response model, since the underlying business schema didn't exist before
this prompt.

Run it locally with `make mcp-run`; test it with `make mcp-test`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add Dispute MCP Server section to README"
```

---

### Task 15: Full verification run

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-14.

- [ ] **Step 1: Run `make verify` from the repo root**

Run: `make verify`
Expected: Ruff format-check passes, Ruff lint passes, strict Mypy passes (including `dispute-mcp-server`), the full pytest suite passes (all prior packages' tests plus every new `dispute-mcp-server` test), and the `investigator-ui` build still succeeds unchanged.

- [ ] **Step 2: Run the targeted registry-equivalent verification for this package**

Run: `uv run pytest dispute-mcp-server/tests -q` and `uv run mypy dispute-mcp-server/src dispute-mcp-server/tests`
Expected: both clean.

- [ ] **Step 3: If anything fails**

Fix the specific file the error points to. Do not weaken Ruff/Mypy/TypeScript strictness. Re-run `make verify` until clean. Commit each fix separately with a clear, specific message.

- [ ] **Step 4: Confirm working tree is clean and pre-existing files untouched**

Run: `git status --short`
Expected: no output. Also confirm (`git log --oneline <batch-start>..HEAD -- .gitignore tmp/` returns nothing) that the pre-existing `.gitignore` modification and `tmp/prompts/*.md` files were never touched by this batch.

---

### Task 16: Consolidated changelog commit

**Files:**
- Modify: `docs/COMMIT_LOG.md`

**Interfaces:**
- Consumes: the full commit history produced by Tasks 1-15.

Per the user's explicit instruction: the changelog is written and
committed **once**, covering every individual commit made in Tasks 1-15 —
not per-commit. Per the lesson from Prompt 1 (a fresh subagent mistakenly
wrote premature entries mid-batch), **this task should be performed
directly by the controller**, not delegated to a fresh subagent.

- [ ] **Step 1: List this batch's commits for reference**

Run: `git log --oneline <task-1-base-sha>..HEAD`
(the base SHA is the commit immediately before Task 1 started, recorded in
the progress ledger when this plan begins execution).

- [ ] **Step 2: Prepend entries to `docs/COMMIT_LOG.md`**

Add one entry per logical unit of work (dependencies; models; seed data;
repository; config/logging; case tools; transaction tools; customer
tools; merchant tools; main.py/startup; mypy cleanup; docker-compose;
Makefile; README; any fix commits from Task 15), most recent first, above
the existing top entry. Use today's actual date and the real filenames
touched.

- [ ] **Step 3: Commit**

```bash
git add docs/COMMIT_LOG.md
git commit -m "docs: log Prompt 3 dispute-mcp-server batch"
```

---

## Self-Review Notes

- **Spec coverage:** all 4 tool groups (13 tools) map to Tasks 6-9; seed
  data consistency, structured logging, server startup, and tool discovery
  each get a dedicated test file (Tasks 3-4, 5, 10); Docker/Makefile/README
  map to Tasks 12-14; full verification and changelog close the batch
  (Tasks 15-16).
- **No placeholders:** every step has complete, real code, including all
  seed data records and cross-references.
- **Contract-reuse boundary respected:** only `chargeback_contracts.mcp`'s
  write-side envelope types are imported; nothing is added to
  `chargeback_contracts` in this plan.
- **No business decisions:** every tool is a lookup or a narrow mutation
  (case status, audit append) — no dispute-type-to-recommendation logic,
  no orchestration, no specialist behavior anywhere in this plan.
- **Docker reality-check:** Task 12 explicitly requires recording whether
  `docker compose config` could actually run in the execution
  environment, rather than claiming an untested container build works.
