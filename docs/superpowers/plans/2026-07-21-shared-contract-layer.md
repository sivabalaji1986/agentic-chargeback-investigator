# Shared Contract Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete shared, strongly-typed Pydantic v2 contract layer in the existing `contracts` package (import name `chargeback_contracts`), covering every stable payload that crosses a boundary in the future system (A2A, Agent Registry, AG-UI, A2UI, MCP, audit persistence). Contracts and validation only.

**Architecture:** 13 focused modules forming a DAG (no cycles): `common.py` (leaf) → `skills.py` → `evidence.py` → `dispute.py` → `findings.py` → `policy.py` → `recommendation.py` → `agui.py` / `a2ui.py` / `decisions.py` → `mcp.py` → `records.py` (root). `__init__.py` re-exports the public surface. Two existing packages (`orchestrator-agent`, `transaction-agent`) get a workspace dependency on `contracts` plus one integration test each, proving the package is actually consumable.

**Tech Stack:** Python 3.13, Pydantic v2 (`pydantic>=2.13`), `a2a-sdk==1.1.1` (protobuf-backed `a2a.types`; referenced for ID-shape awareness only — no embedding), `ag-ui-protocol==0.1.19` (`ag_ui.core`, Pydantic-based), `uv` workspace.

## Global Constraints

- Contracts and validation only — no Agent Registry endpoints, orchestrator workflow, specialist agents, MCP tools, RAG/ChromaDB, Ollama, AG-UI streaming server, React UI, A2UI renderer, deterministic recommendation *engine*, persistence, or mock business services.
- Every application-owned model: Pydantic v2, `model_config = ConfigDict(extra="forbid")`, JSON-safe, JSON round-trippable, string-backed enums, timezone-aware UTC datetimes, `Decimal` for money with a separate ISO 4217 currency code, explicit typed fields (no untyped dicts), `Field` constraints for non-empty IDs/percentages, no `Any` (none needed — verified during design research), no mutable defaults (bare `()` tuple defaults are safe, not mutable), concise docstrings where business meaning isn't obvious, snake_case internals, protocol aliases only where an external protocol requires them (none needed for our own contracts in this prompt). No confidence scores anywhere.
- **a2a.types is protobuf-backed in a2a-sdk 1.1.1** (confirmed by direct inspection): `Task.id`, `Task.context_id`, `AgentSkill.id` are plain strings. Contracts reference A2A identifiers as validated non-blank `str | None` fields (`a2a_task_id`, `a2a_context_id`) — never construct, wrap, subclass, or duplicate `a2a.types.AgentCard`/`AgentSkill`/`Task`/`Message`/`Artifact`/`Part`/`TaskState`.
- **ag_ui.core is Pydantic v2** (confirmed by direct inspection): the extension point for app events is `CustomEvent(type=EventType.CUSTOM, name: str, value: Any)`. Contracts define the typed `value` payload models only — not `CustomEvent` subclasses, not the streaming server.
- A2UI has no official SDK; all A2UI payloads are new models. A2UI version is exactly `"0.9"` (a `Literal["0.9"]` field type enforces this structurally).
- Specialists (`SpecialistFinding`) never carry a recommendation field — enforced by the model simply having none. Policy (`PolicyInterpretation`) never carries a recommendation field either.
- `InvestigationRecommendation.recommendation`/`.reason_codes` (deterministic) and `.explanation` (descriptive) are independent fields — changing one never requires changing the other.
- `mcp.py`'s `get_case`/`get_transaction` read results stay deliberately minimal (no invented business schema); `get_customer_history` reuses `CustomerHistoryFindingDetails`; `get_merchant_evidence`/`list_case_documents` reuse `EvidenceRef`.
- Pre-existing, already-committed repo state must not be touched: the `.gitignore` `tmp` line and `tmp/prompts/Prompt01.md` / `tmp/prompts/Prompt02.md` (now committed by the user directly — do not amend or interact with that commit).
- Commit workflow for this batch (explicit user instruction): every created/modified file gets its own `git add <file> && git commit`, with **no** `docs/COMMIT_LOG.md` touch until the final task, which adds every entry in one consolidated commit. (Lesson carried from Prompt 1: a fresh subagent previously wrote premature `COMMIT_LOG.md` entries mid-batch — every task dispatch in this plan must explicitly forbid touching that file until the final task.)
- `make verify` must stay green throughout (ruff format-check, ruff lint, strict mypy for production *and* test code within the narrowed scope, full pytest suite, `investigator-ui` build).

---

### Task 1: Add contracts package runtime dependencies

**Files:**
- Modify: `contracts/pyproject.toml`

**Interfaces:**
- Produces: `pydantic`, `a2a-sdk==1.1.1`, `ag-ui-protocol==0.1.19` available to every later task in this plan.

- [ ] **Step 1: Update `contracts/pyproject.toml`**

Current content (from Prompt 1):
```toml
[project]
name = "contracts"
version = "0.1.0"
description = "Shared Pydantic models and capability constants"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/chargeback_contracts"]
```

Replace the `dependencies` line:
```toml
[project]
name = "contracts"
version = "0.1.0"
description = "Shared Pydantic models and capability constants"
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.13",
    "a2a-sdk==1.1.1",
    "ag-ui-protocol==0.1.19",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/chargeback_contracts"]
```

- [ ] **Step 2: Lock and sync**

Run: `uv lock && uv sync --all-packages`
Expected: resolves cleanly. `a2a-sdk==1.1.1` and `ag-ui-protocol==0.1.19` were both confirmed to exist on the live PyPI registry during design research (2026-07-21) — if resolution fails for either, STOP and report BLOCKED with the exact error rather than substituting a version.

- [ ] **Step 3: Commit**

```bash
git add contracts/pyproject.toml uv.lock
git commit -m "chore: add contracts package runtime dependencies (pydantic, a2a-sdk, ag-ui-protocol)"
```

---

### Task 2: `common.py` — shared primitives

**Files:**
- Create: `contracts/src/chargeback_contracts/common.py`
- Modify: `contracts/tests/test_import.py` → rename/replace with `contracts/tests/test_common.py` (delete the old file; this task removes it since Task 14 replaces public-surface import testing properly — for this task, just delete `contracts/tests/test_import.py` and create `test_common.py` in its place)

**Interfaces:**
- Produces: `ContractModel` (base class, `extra="forbid"`), `require_non_blank`, `require_utc`, `require_currency_code`, `require_positive_amount`, `require_percentage` — used by every other module in this plan.

- [ ] **Step 1: Delete the Prompt 1 smoke test**

```bash
git rm contracts/tests/test_import.py
```

- [ ] **Step 2: Write `contracts/src/chargeback_contracts/common.py`**

```python
"""Shared primitives used across the contract layer.

Leaf module: common.py must never import from any sibling contract module.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")


class ContractModel(BaseModel):
    """Base class for every application-owned contract model.

    Rejects unknown fields so producers and consumers stay in lockstep
    across service boundaries.
    """

    model_config = ConfigDict(extra="forbid")


def require_non_blank(value: str, *, field_name: str) -> str:
    """Reject empty or whitespace-only identifiers."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def require_utc(value: datetime, *, field_name: str) -> datetime:
    """Require a timezone-aware datetime, normalized to UTC."""
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def require_currency_code(value: str) -> str:
    """Validate an ISO 4217 three-letter uppercase currency code."""
    if not _CURRENCY_CODE_RE.match(value):
        raise ValueError("currency must be a three-letter uppercase ISO 4217 code")
    return value


def require_positive_amount(value: Decimal) -> Decimal:
    """Require a strictly positive monetary amount."""
    if value <= 0:
        raise ValueError("amount must be positive")
    return value


def require_percentage(value: Decimal) -> Decimal:
    """Require a percentage value within the inclusive bounds [0, 100]."""
    if value < 0 or value > 100:
        raise ValueError("percentage must be between 0 and 100")
    return value
```

- [ ] **Step 3: Write `contracts/tests/test_common.py`**

```python
"""Tests for chargeback_contracts.common."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from chargeback_contracts.common import (
    ContractModel,
    require_currency_code,
    require_non_blank,
    require_percentage,
    require_positive_amount,
    require_utc,
)


class _Example(ContractModel):
    name: str


def test_contract_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _Example(name="ok", extra_field="not allowed")


def test_require_non_blank_rejects_blank() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        require_non_blank("   ", field_name="case_id")


def test_require_non_blank_accepts_value() -> None:
    assert require_non_blank("CASE-1", field_name="case_id") == "CASE-1"


def test_require_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        require_utc(datetime(2026, 1, 1), field_name="submitted_at")  # noqa: DTZ001


def test_require_utc_normalizes_to_utc() -> None:
    aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert require_utc(aware, field_name="submitted_at") == aware


def test_require_currency_code_rejects_lowercase() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        require_currency_code("usd")


def test_require_currency_code_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        require_currency_code("US")


def test_require_currency_code_accepts_valid() -> None:
    assert require_currency_code("USD") == "USD"


def test_require_positive_amount_rejects_zero_and_negative() -> None:
    with pytest.raises(ValueError, match="positive"):
        require_positive_amount(Decimal("0"))
    with pytest.raises(ValueError, match="positive"):
        require_positive_amount(Decimal("-1.00"))


def test_require_positive_amount_accepts_positive() -> None:
    assert require_positive_amount(Decimal("12.50")) == Decimal("12.50")


def test_require_percentage_rejects_out_of_bounds() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        require_percentage(Decimal("-1"))
    with pytest.raises(ValueError, match="between 0 and 100"):
        require_percentage(Decimal("101"))


def test_require_percentage_accepts_bounds() -> None:
    assert require_percentage(Decimal("0")) == Decimal("0")
    assert require_percentage(Decimal("100")) == Decimal("100")
```

- [ ] **Step 4: Run the focused test**

Run: `uv run pytest contracts/tests/test_common.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add contracts/src/chargeback_contracts/common.py contracts/tests/test_common.py
git rm --cached contracts/tests/test_import.py 2>/dev/null || true
git commit -m "feat: add contracts common primitives (ContractModel, validators)"
```

---

### Task 3: `skills.py` — skill IDs, dispute types, and the required-skill mapping

**Files:**
- Create: `contracts/src/chargeback_contracts/skills.py`
- Create: `contracts/tests/test_skills.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common` (nothing needed directly, but stays consistent with the DAG).
- Produces: `SkillId`, `DisputeType`, `CORE_EVIDENCE_SKILL_IDS`, `POLICY_SKILL_ID`, `DUPLICATE_TRANSACTION_SKILL_ID`, `required_skills_for(dispute_type, *, include_policy=True)` — consumed by `dispute.py`, `findings.py`, `policy.py`, `agui.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/skills.py`**

```python
"""Skill identifiers, dispute types, and the deterministic mapping between
them.

This module represents the dependency between evidence specialists and the
Policy specialist declaratively — it does not execute orchestration.
"""

from __future__ import annotations

from enum import Enum


class SkillId(str, Enum):
    """Stable skill identifiers shared by the Agent Registry, agents, and Orchestrator."""

    TRANSACTION_INVESTIGATION = "transaction-investigation"
    CUSTOMER_HISTORY_INVESTIGATION = "customer-history-investigation"
    MERCHANT_EVIDENCE_INVESTIGATION = "merchant-evidence-investigation"
    CHARGEBACK_POLICY_INTERPRETATION = "chargeback-policy-interpretation"
    DUPLICATE_TRANSACTION_INVESTIGATION = "duplicate-transaction-investigation"


class DisputeType(str, Enum):
    """Supported initial chargeback dispute classifications."""

    GOODS_NOT_RECEIVED = "goods_not_received"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    CANCELLED_SERVICE = "cancelled_service"
    MERCHANT_ERROR = "merchant_error"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    OTHER = "other"


CORE_EVIDENCE_SKILL_IDS: frozenset[SkillId] = frozenset(
    {
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    }
)

POLICY_SKILL_ID: SkillId = SkillId.CHARGEBACK_POLICY_INTERPRETATION

DUPLICATE_TRANSACTION_SKILL_ID: SkillId = SkillId.DUPLICATE_TRANSACTION_INVESTIGATION

_DISPUTE_TYPE_MAPPED_SKILLS: dict[DisputeType, tuple[SkillId, ...]] = {
    DisputeType.GOODS_NOT_RECEIVED: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.DUPLICATE_TRANSACTION: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.DUPLICATE_TRANSACTION_INVESTIGATION,
    ),
    DisputeType.CANCELLED_SERVICE: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.MERCHANT_ERROR: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.CARD_NOT_PRESENT_FRAUD: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
    ),
    DisputeType.OTHER: (SkillId.TRANSACTION_INVESTIGATION,),
}


def required_skills_for(
    dispute_type: DisputeType, *, include_policy: bool = True
) -> tuple[SkillId, ...]:
    """Return the deterministic skill IDs required to investigate a dispute type.

    The evidence-specialist skills always run first; the Policy skill (when
    ``include_policy`` is true, the default) is appended last, since Policy
    interprets findings only after the evidence specialists have reported.
    """
    mapped = _DISPUTE_TYPE_MAPPED_SKILLS[dispute_type]
    if include_policy:
        return (*mapped, POLICY_SKILL_ID)
    return mapped
```

- [ ] **Step 2: Write `contracts/tests/test_skills.py`**

```python
"""Tests for chargeback_contracts.skills."""

from chargeback_contracts.skills import (
    CORE_EVIDENCE_SKILL_IDS,
    DUPLICATE_TRANSACTION_SKILL_ID,
    POLICY_SKILL_ID,
    DisputeType,
    SkillId,
    required_skills_for,
)


def test_skill_id_stable_values() -> None:
    assert SkillId.TRANSACTION_INVESTIGATION.value == "transaction-investigation"
    assert SkillId.CUSTOMER_HISTORY_INVESTIGATION.value == "customer-history-investigation"
    assert SkillId.MERCHANT_EVIDENCE_INVESTIGATION.value == "merchant-evidence-investigation"
    assert SkillId.CHARGEBACK_POLICY_INTERPRETATION.value == "chargeback-policy-interpretation"
    assert (
        SkillId.DUPLICATE_TRANSACTION_INVESTIGATION.value
        == "duplicate-transaction-investigation"
    )


def test_dispute_type_stable_values() -> None:
    assert DisputeType.GOODS_NOT_RECEIVED.value == "goods_not_received"
    assert DisputeType.DUPLICATE_TRANSACTION.value == "duplicate_transaction"
    assert DisputeType.CANCELLED_SERVICE.value == "cancelled_service"
    assert DisputeType.MERCHANT_ERROR.value == "merchant_error"
    assert DisputeType.CARD_NOT_PRESENT_FRAUD.value == "card_not_present_fraud"
    assert DisputeType.OTHER.value == "other"


def test_core_evidence_skill_ids_excludes_policy_and_duplicate() -> None:
    assert POLICY_SKILL_ID not in CORE_EVIDENCE_SKILL_IDS
    assert DUPLICATE_TRANSACTION_SKILL_ID not in CORE_EVIDENCE_SKILL_IDS
    assert len(CORE_EVIDENCE_SKILL_IDS) == 3


def test_required_skills_for_appends_policy_last_by_default() -> None:
    skills = required_skills_for(DisputeType.GOODS_NOT_RECEIVED)
    assert skills[-1] == POLICY_SKILL_ID
    assert skills[:-1] == (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    )


def test_required_skills_for_can_exclude_policy() -> None:
    skills = required_skills_for(DisputeType.OTHER, include_policy=False)
    assert skills == (SkillId.TRANSACTION_INVESTIGATION,)


def test_duplicate_transaction_dispute_requires_duplicate_skill() -> None:
    skills = required_skills_for(DisputeType.DUPLICATE_TRANSACTION, include_policy=False)
    assert DUPLICATE_TRANSACTION_SKILL_ID in skills
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_skills.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/skills.py contracts/tests/test_skills.py
git commit -m "feat: add skill IDs, dispute types, and dispute-to-skill mapping"
```

---

### Task 4: `evidence.py` — evidence references

**Files:**
- Create: `contracts/src/chargeback_contracts/evidence.py`
- Create: `contracts/tests/test_evidence.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common` (`ContractModel`, `require_non_blank`, `require_utc`).
- Produces: `EvidenceType`, `EvidenceRef` — consumed by `dispute.py`, `findings.py`, `policy.py`, `a2ui.py`, `mcp.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/evidence.py`**

```python
"""Evidence reference contracts.

Evidence references carry a secure pointer to evidence content; they must
never carry raw file bytes, and must never expose a local filesystem path.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc

ALLOWED_EVIDENCE_URI_SCHEMES: tuple[str, ...] = ("evidence://",)


class EvidenceType(str, Enum):
    """Supported evidence categories for a chargeback investigation."""

    CUSTOMER_DECLARATION = "customer_declaration"
    TRANSACTION_STATEMENT = "transaction_statement"
    MERCHANT_EMAIL = "merchant_email"
    MERCHANT_CHAT = "merchant_chat"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    CANCELLATION_CONFIRMATION = "cancellation_confirmation"
    DELIVERY_PROOF = "delivery_proof"
    REFUND_REQUEST = "refund_request"
    POLICE_REPORT = "police_report"
    SCREENSHOT = "screenshot"
    OTHER = "other"


class EvidenceRef(ContractModel):
    """A pointer to evidence content — never the content itself."""

    evidence_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    display_name: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    uploaded_at: datetime
    source: str = Field(min_length=1)
    checksum: str | None = None
    description: str | None = None

    @field_validator("evidence_id", "case_id", "display_name", "media_type", "source")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("uri")
    @classmethod
    def _safe_uri(cls, value: str) -> str:
        if not value.startswith(ALLOWED_EVIDENCE_URI_SCHEMES):
            raise ValueError(
                f"evidence uri must use one of {ALLOWED_EVIDENCE_URI_SCHEMES}, got: {value!r}"
            )
        return value

    @field_validator("uploaded_at")
    @classmethod
    def _uploaded_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="uploaded_at")
```

Note: pydantic v2's `field_validator` classmethods receive a `ValidationInfo` object as the second positional argument when declared with two parameters; annotate it precisely rather than `object` if mypy complains — see Task 15's verification step for the authoritative fix if this surfaces a real error (don't guess preemptively; the `# type: ignore[attr-defined]` above is a placeholder hedge — replace it with the correct `pydantic.ValidationInfo` type annotation once mypy actually runs against this file in Task 14, and remove the ignore comment if it's then unnecessary).

- [ ] **Step 2: Write `contracts/tests/test_evidence.py`**

```python
"""Tests for chargeback_contracts.evidence."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.evidence import EvidenceRef, EvidenceType


def _valid_evidence_ref(**overrides: object) -> EvidenceRef:
    defaults: dict[str, object] = {
        "evidence_id": "EVID-1",
        "case_id": "CASE-1",
        "evidence_type": EvidenceType.RECEIPT,
        "display_name": "receipt.pdf",
        "media_type": "application/pdf",
        "uri": "evidence://case-1/receipt.pdf",
        "uploaded_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "source": "web_form",
    }
    defaults.update(overrides)
    return EvidenceRef(**defaults)  # type: ignore[arg-type]


def test_valid_evidence_ref_round_trips_through_json() -> None:
    ref = _valid_evidence_ref()
    restored = EvidenceRef.model_validate_json(ref.model_dump_json())
    assert restored == ref


def test_evidence_type_stable_values() -> None:
    assert EvidenceType.CUSTOMER_DECLARATION.value == "customer_declaration"
    assert EvidenceType.TRANSACTION_STATEMENT.value == "transaction_statement"
    assert EvidenceType.MERCHANT_EMAIL.value == "merchant_email"
    assert EvidenceType.MERCHANT_CHAT.value == "merchant_chat"
    assert EvidenceType.RECEIPT.value == "receipt"
    assert EvidenceType.INVOICE.value == "invoice"
    assert EvidenceType.CANCELLATION_CONFIRMATION.value == "cancellation_confirmation"
    assert EvidenceType.DELIVERY_PROOF.value == "delivery_proof"
    assert EvidenceType.REFUND_REQUEST.value == "refund_request"
    assert EvidenceType.POLICE_REPORT.value == "police_report"
    assert EvidenceType.SCREENSHOT.value == "screenshot"
    assert EvidenceType.OTHER.value == "other"


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_evidence_ref(unexpected_field="nope")


def test_rejects_local_filesystem_path() -> None:
    with pytest.raises(ValidationError, match="evidence uri must use one of"):
        _valid_evidence_ref(uri="/etc/passwd")


def test_rejects_file_scheme() -> None:
    with pytest.raises(ValidationError, match="evidence uri must use one of"):
        _valid_evidence_ref(uri="file:///etc/passwd")


def test_rejects_blank_evidence_id() -> None:
    with pytest.raises(ValidationError):
        _valid_evidence_ref(evidence_id="   ")


def test_rejects_naive_uploaded_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_evidence_ref(uploaded_at=datetime(2026, 1, 1))  # noqa: DTZ001
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_evidence.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/evidence.py contracts/tests/test_evidence.py
git commit -m "feat: add evidence reference contracts with URI scheme validation"
```

---

### Task 5: `dispute.py` — dispute intake contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/dispute.py`
- Create: `contracts/tests/test_dispute.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common` (`ContractModel`, `require_non_blank`, `require_utc`, `require_currency_code`, `require_positive_amount`), `chargeback_contracts.skills` (`DisputeType`, `SkillId`), `chargeback_contracts.evidence` (`EvidenceRef`).
- Produces: `SourceChannel`, `InvestigationRequest` — consumed by `records.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/dispute.py`**

```python
"""Dispute intake contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import (
    ContractModel,
    require_currency_code,
    require_non_blank,
    require_positive_amount,
    require_utc,
)
from chargeback_contracts.evidence import EvidenceRef
from chargeback_contracts.skills import DisputeType, SkillId


class SourceChannel(str, Enum):
    """Channel through which the customer submitted the dispute."""

    EMAIL = "email"
    CONTACT_CENTRE = "contact_centre"
    WEB_FORM = "web_form"
    CHATBOT = "chatbot"


class InvestigationRequest(ContractModel):
    """Intake payload describing a single chargeback dispute to investigate."""

    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    source_channel: SourceChannel
    customer_narrative: str = Field(min_length=1)
    dispute_type: DisputeType
    amount: Decimal
    currency: str
    submitted_at: datetime
    evidence_refs: tuple[EvidenceRef, ...] = ()
    requested_skill_ids: tuple[SkillId, ...] = ()
    a2a_context_id: str | None = None

    @field_validator("investigation_id", "case_id", "transaction_id", "customer_narrative")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        return require_currency_code(value)

    @field_validator("amount")
    @classmethod
    def _amount(cls, value: Decimal) -> Decimal:
        return require_positive_amount(value)

    @field_validator("submitted_at")
    @classmethod
    def _submitted_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="submitted_at")

    @field_validator("a2a_context_id")
    @classmethod
    def _context_id(cls, value: str | None) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name="a2a_context_id")
        return value
```

- [ ] **Step 2: Write `contracts/tests/test_dispute.py`**

```python
"""Tests for chargeback_contracts.dispute."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from chargeback_contracts.dispute import InvestigationRequest, SourceChannel
from chargeback_contracts.skills import DisputeType, SkillId


def _valid_request(**overrides: object) -> InvestigationRequest:
    defaults: dict[str, object] = {
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "transaction_id": "TXN-1",
        "source_channel": SourceChannel.WEB_FORM,
        "customer_narrative": "Item never arrived.",
        "dispute_type": DisputeType.GOODS_NOT_RECEIVED,
        "amount": Decimal("99.99"),
        "currency": "USD",
        "submitted_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "requested_skill_ids": (SkillId.TRANSACTION_INVESTIGATION,),
    }
    defaults.update(overrides)
    return InvestigationRequest(**defaults)  # type: ignore[arg-type]


def test_valid_request_round_trips_through_json() -> None:
    request = _valid_request()
    restored = InvestigationRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_source_channel_stable_values() -> None:
    assert SourceChannel.EMAIL.value == "email"
    assert SourceChannel.CONTACT_CENTRE.value == "contact_centre"
    assert SourceChannel.WEB_FORM.value == "web_form"
    assert SourceChannel.CHATBOT.value == "chatbot"


def test_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError, match="positive"):
        _valid_request(amount=Decimal("0"))


def test_rejects_lowercase_currency() -> None:
    with pytest.raises(ValidationError, match="ISO 4217"):
        _valid_request(currency="usd")


def test_rejects_naive_submitted_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_request(submitted_at=datetime(2026, 1, 1))  # noqa: DTZ001


def test_rejects_blank_context_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _valid_request(a2a_context_id="   ")


def test_allows_omitted_context_id() -> None:
    request = _valid_request()
    assert request.a2a_context_id is None


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_request(unexpected_field="nope")
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_dispute.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/dispute.py contracts/tests/test_dispute.py
git commit -m "feat: add dispute intake contracts (InvestigationRequest, SourceChannel)"
```

---

### Task 6: `findings.py` — specialist finding contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/findings.py`
- Create: `contracts/tests/test_findings.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.skills` (`SkillId`), `chargeback_contracts.evidence` (`EvidenceRef`, `EvidenceType`).
- Produces: `FindingStatus`, `TransactionFindingDetails`, `CustomerHistoryFindingDetails`, `MerchantEvidenceFindingDetails`, `SpecialistFinding` — consumed by `records.py`; `CustomerHistoryFindingDetails` also reused by `mcp.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/findings.py`**

```python
"""Specialist finding contracts.

Specialists investigate and report facts. A SpecialistFinding must never
carry the final Accept / Reject / Request More Evidence recommendation —
enforced structurally by this module simply defining no such field.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, field_validator, model_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.skills import SkillId


class FindingStatus(str, Enum):
    """Completion state of a specialist's investigation."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TransactionFindingDetails(ContractModel):
    """Structured facts produced by the Transaction specialist."""

    kind: Literal["transaction"] = "transaction"
    transaction_matched: bool
    posted_at: datetime | None = None
    merchant: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    authorization_reference: str | None = None
    related_transaction_ids: tuple[str, ...] = ()
    timeline_observations: tuple[str, ...] = ()


class CustomerHistoryFindingDetails(ContractModel):
    """Structured facts produced by the Customer History specialist.

    Also reused by ``mcp.py`` for the ``get_customer_history`` read result,
    since the shape of "customer history facts" is identical in both places.
    """

    kind: Literal["customer_history"] = "customer_history"
    previous_dispute_count: int = Field(ge=0)
    previous_refund_count: int = Field(ge=0)
    prior_similar_claim_ids: tuple[str, ...] = ()
    customer_tenure_days: int | None = Field(default=None, ge=0)
    observations: tuple[str, ...] = ()


class MerchantEvidenceFindingDetails(ContractModel):
    """Structured facts produced by the Merchant Evidence specialist."""

    kind: Literal["merchant_evidence"] = "merchant_evidence"
    evidence_ids_reviewed: tuple[str, ...] = ()
    merchant_acknowledgement: bool | None = None
    cancellation_evidence_found: bool | None = None
    delivery_evidence_found: bool | None = None
    refund_evidence_found: bool | None = None
    authenticity_observations: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()


FindingDetails = Annotated[
    Union[TransactionFindingDetails, CustomerHistoryFindingDetails, MerchantEvidenceFindingDetails],
    Field(discriminator="kind"),
]


class SpecialistFinding(ContractModel):
    """Common envelope for a specialist's reported facts.

    Never carries a recommendation — ownership of the final recommendation
    stays with the deterministic recommendation engine, not the specialist.
    """

    finding_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    producing_agent_id: str = Field(min_length=1)
    skill_id: SkillId
    status: FindingStatus
    summary: str = Field(min_length=1)
    details: FindingDetails
    evidence_refs_used: tuple[EvidenceRef, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    warnings: tuple[str, ...] = ()
    started_at: datetime
    completed_at: datetime | None = None
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator("finding_id", "investigation_id", "case_id", "producing_agent_id", "summary")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("started_at")
    @classmethod
    def _started_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="started_at")

    @field_validator("completed_at")
    @classmethod
    def _completed_at(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return require_utc(value, field_name="completed_at")
        return value

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: object) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]
        return value

    @model_validator(mode="after")
    def _validate_status_rules(self) -> "SpecialistFinding":
        if self.status == FindingStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed findings require a completion timestamp")
        if self.status == FindingStatus.PARTIAL and not (self.warnings or self.missing_evidence):
            raise ValueError("partial findings must contain warnings or missing evidence")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        return self
```

- [ ] **Step 2: Write `contracts/tests/test_findings.py`**

```python
"""Tests for chargeback_contracts.findings."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.findings import (
    CustomerHistoryFindingDetails,
    FindingStatus,
    MerchantEvidenceFindingDetails,
    SpecialistFinding,
    TransactionFindingDetails,
)
from chargeback_contracts.skills import SkillId


def _completed_finding(**overrides: object) -> SpecialistFinding:
    defaults: dict[str, object] = {
        "finding_id": "FIND-1",
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "producing_agent_id": "transaction-agent",
        "skill_id": SkillId.TRANSACTION_INVESTIGATION,
        "status": FindingStatus.COMPLETED,
        "summary": "Transaction confirmed as posted.",
        "details": TransactionFindingDetails(transaction_matched=True),
        "started_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return SpecialistFinding(**defaults)  # type: ignore[arg-type]


def test_completed_finding_round_trips_through_json() -> None:
    finding = _completed_finding()
    restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
    assert restored == finding


def test_discriminated_details_round_trip_for_each_kind() -> None:
    customer_history = _completed_finding(
        skill_id=SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        details=CustomerHistoryFindingDetails(previous_dispute_count=2, previous_refund_count=1),
    )
    merchant_evidence = _completed_finding(
        skill_id=SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
        details=MerchantEvidenceFindingDetails(merchant_acknowledgement=True),
    )
    for finding in (customer_history, merchant_evidence):
        restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
        assert restored == finding
        assert type(restored.details) is type(finding.details)


def test_finding_has_no_recommendation_field() -> None:
    assert "recommendation" not in SpecialistFinding.model_fields


def test_completed_status_requires_completed_at() -> None:
    with pytest.raises(ValidationError, match="require a completion timestamp"):
        _completed_finding(completed_at=None)


def test_completed_at_cannot_precede_started_at() -> None:
    with pytest.raises(ValidationError, match="cannot precede started_at"):
        _completed_finding(
            started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_partial_status_requires_warnings_or_missing_evidence() -> None:
    with pytest.raises(ValidationError, match="warnings or missing evidence"):
        _completed_finding(status=FindingStatus.PARTIAL, completed_at=None, warnings=(), missing_evidence=())


def test_partial_status_accepts_warnings() -> None:
    finding = _completed_finding(status=FindingStatus.PARTIAL, completed_at=None, warnings=("delay",))
    assert finding.status == FindingStatus.PARTIAL


def test_failed_status_requires_non_blank_summary() -> None:
    with pytest.raises(ValidationError):
        _completed_finding(status=FindingStatus.FAILED, completed_at=None, summary="   ")


def test_rejects_blank_a2a_task_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _completed_finding(a2a_task_id="   ")
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_findings.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/findings.py contracts/tests/test_findings.py
git commit -m "feat: add specialist finding contracts with discriminated detail payloads"
```

---

### Task 7: `policy.py` — policy interpretation contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/policy.py`
- Create: `contracts/tests/test_policy.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.skills` (`DisputeType`), `chargeback_contracts.evidence` (`EvidenceType`).
- Produces: `PolicyInterpretation` — consumed by `records.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/policy.py`**

```python
"""Policy interpretation contracts.

The Policy Agent interprets policy but never decides the final
recommendation — enforced structurally by this module defining no
recommendation field, and by running only after the evidence specialists
(see chargeback_contracts.skills.required_skills_for).
"""

from __future__ import annotations

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.skills import DisputeType


class PolicyInterpretation(ContractModel):
    """The Policy specialist's interpretation of applicable chargeback policy."""

    investigation_id: str = Field(min_length=1)
    dispute_type: DisputeType
    policy_version: str = Field(min_length=1)
    cited_sections: tuple[str, ...] = ()
    applicable_rules: tuple[str, ...] = ()
    required_evidence: tuple[EvidenceType, ...] = ()
    satisfied_evidence: tuple[EvidenceType, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    exceptions_or_escalations: tuple[str, ...] = ()
    interpretation_summary: str = Field(min_length=1)
    source_references: tuple[str, ...] = ()
    producing_agent_id: str = Field(min_length=1)
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator(
        "investigation_id", "policy_version", "interpretation_summary", "producing_agent_id"
    )
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: object) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]
        return value
```

- [ ] **Step 2: Write `contracts/tests/test_policy.py`**

```python
"""Tests for chargeback_contracts.policy."""

import pytest
from pydantic import ValidationError

from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.policy import PolicyInterpretation
from chargeback_contracts.skills import DisputeType


def _valid_interpretation(**overrides: object) -> PolicyInterpretation:
    defaults: dict[str, object] = {
        "investigation_id": "INV-1",
        "dispute_type": DisputeType.GOODS_NOT_RECEIVED,
        "policy_version": "2026.1",
        "required_evidence": (EvidenceType.DELIVERY_PROOF,),
        "missing_evidence": (EvidenceType.DELIVERY_PROOF,),
        "interpretation_summary": "Delivery proof required and not yet provided.",
        "producing_agent_id": "policy-agent",
    }
    defaults.update(overrides)
    return PolicyInterpretation(**defaults)  # type: ignore[arg-type]


def test_valid_interpretation_round_trips_through_json() -> None:
    interpretation = _valid_interpretation()
    restored = PolicyInterpretation.model_validate_json(interpretation.model_dump_json())
    assert restored == interpretation


def test_has_no_recommendation_field() -> None:
    assert "recommendation" not in PolicyInterpretation.model_fields


def test_rejects_blank_policy_version() -> None:
    with pytest.raises(ValidationError):
        _valid_interpretation(policy_version="   ")


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_interpretation(unexpected_field="nope")


def test_rejects_blank_a2a_task_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _valid_interpretation(a2a_task_id="   ")
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_policy.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/policy.py contracts/tests/test_policy.py
git commit -m "feat: add policy interpretation contract"
```

---

### Task 8: `recommendation.py` — missing-capability and recommendation contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/recommendation.py`
- Create: `contracts/tests/test_recommendation.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.skills` (`SkillId`), `chargeback_contracts.evidence` (`EvidenceType`).
- Produces: `MissingCapabilityWarning`, `RecommendationType`, `InvestigationRecommendation` — consumed by `agui.py`, `a2ui.py`, `decisions.py`, `records.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/recommendation.py`**

```python
"""Missing-capability and recommendation contracts.

`recommendation` and `reason_codes` on InvestigationRecommendation are
deterministic outputs; `explanation` is descriptive text that may later be
generated by an LLM. Changing the explanation must never require changing
the deterministic fields — they are independent fields, not derived from
one another.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.skills import SkillId


class MissingCapabilityWarning(ContractModel):
    """Explicit representation of an unavailable skill — never a generic exception."""

    required_skill_id: SkillId
    message: str = Field(min_length=1)
    can_continue_partially: bool
    affected_area: str = Field(min_length=1)
    discovered_at: datetime

    @field_validator("message", "affected_area")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("discovered_at")
    @classmethod
    def _discovered_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="discovered_at")


class RecommendationType(str, Enum):
    """The only supported investigation recommendation outcomes."""

    ACCEPT_CHARGEBACK = "accept_chargeback"
    REJECT_CHARGEBACK = "reject_chargeback"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


class InvestigationRecommendation(ContractModel):
    """The deterministic recommendation produced for an investigation."""

    investigation_id: str = Field(min_length=1)
    recommendation: RecommendationType
    reason_codes: tuple[str, ...] = Field(min_length=1)
    supporting_finding_ids: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    missing_capability_warnings: tuple[MissingCapabilityWarning, ...] = ()
    policy_references: tuple[str, ...] = ()
    explanation: str = Field(min_length=1)
    generated_at: datetime

    @field_validator("investigation_id", "explanation")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("generated_at")
    @classmethod
    def _generated_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="generated_at")
```

- [ ] **Step 2: Write `contracts/tests/test_recommendation.py`**

```python
"""Tests for chargeback_contracts.recommendation."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.recommendation import (
    InvestigationRecommendation,
    MissingCapabilityWarning,
    RecommendationType,
)
from chargeback_contracts.skills import SkillId


def _valid_warning(**overrides: object) -> MissingCapabilityWarning:
    defaults: dict[str, object] = {
        "required_skill_id": SkillId.DUPLICATE_TRANSACTION_INVESTIGATION,
        "message": "Duplicate-transaction specialist is not yet registered.",
        "can_continue_partially": True,
        "affected_area": "duplicate transaction check",
        "discovered_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return MissingCapabilityWarning(**defaults)  # type: ignore[arg-type]


def _valid_recommendation(**overrides: object) -> InvestigationRecommendation:
    defaults: dict[str, object] = {
        "investigation_id": "INV-1",
        "recommendation": RecommendationType.REQUEST_MORE_EVIDENCE,
        "reason_codes": ("MISSING_DELIVERY_PROOF",),
        "explanation": "Delivery proof has not yet been provided by the merchant.",
        "generated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return InvestigationRecommendation(**defaults)  # type: ignore[arg-type]


def test_recommendation_type_stable_values() -> None:
    assert RecommendationType.ACCEPT_CHARGEBACK.value == "accept_chargeback"
    assert RecommendationType.REJECT_CHARGEBACK.value == "reject_chargeback"
    assert RecommendationType.REQUEST_MORE_EVIDENCE.value == "request_more_evidence"


def test_valid_recommendation_round_trips_through_json() -> None:
    recommendation = _valid_recommendation()
    restored = InvestigationRecommendation.model_validate_json(recommendation.model_dump_json())
    assert restored == recommendation


def test_missing_capability_warning_round_trips_through_json() -> None:
    warning = _valid_warning()
    restored = MissingCapabilityWarning.model_validate_json(warning.model_dump_json())
    assert restored == warning


def test_reason_codes_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        _valid_recommendation(reason_codes=())


def test_explanation_independent_of_recommendation_fields() -> None:
    a = _valid_recommendation(explanation="Original explanation.")
    b = a.model_copy(update={"explanation": "Regenerated by an LLM."})
    assert a.recommendation == b.recommendation
    assert a.reason_codes == b.reason_codes
    assert a.explanation != b.explanation


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_recommendation(unexpected_field="nope")


def test_warning_rejects_naive_discovered_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_warning(discovered_at=datetime(2026, 1, 1))  # noqa: DTZ001
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_recommendation.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/recommendation.py contracts/tests/test_recommendation.py
git commit -m "feat: add missing-capability and deterministic recommendation contracts"
```

---

### Task 9: `agui.py` — AG-UI application event payloads

**Files:**
- Create: `contracts/src/chargeback_contracts/agui.py`
- Create: `contracts/tests/test_agui.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.skills` (`SkillId`), `chargeback_contracts.evidence` (`EvidenceType`), `chargeback_contracts.recommendation` (`RecommendationType`, `MissingCapabilityWarning`), `chargeback_contracts.skills` (`DisputeType`).
- Produces: 14 event payload classes, each with a stable `event_name` — consumed by nothing else in this plan (leaf-ward, only `__init__.py` re-exports it).

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/agui.py`**

```python
"""AG-UI application event payloads.

These are the typed `value` payloads for `ag_ui.core.CustomEvent`
(`type=EventType.CUSTOM`) — not CustomEvent subclasses themselves, and not
the streaming server that would construct CustomEvent instances (out of
scope for this prompt). Official AG-UI event types come from
`ag_ui.core`; only application-owned payloads are defined here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId


class AgUiEventPayload(ContractModel):
    """Correlation fields shared by every AG-UI custom event payload."""

    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    sequence: int | None = Field(default=None, ge=0)
    occurred_at: datetime
    agent_id: str | None = None
    skill_id: SkillId | None = None

    @field_validator("investigation_id", "case_id", "run_id")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="occurred_at")


class InvestigationAcceptedEvent(AgUiEventPayload):
    event_name: Literal["investigation.accepted"] = "investigation.accepted"
    dispute_type: DisputeType
    requested_skill_ids: tuple[SkillId, ...] = ()


class CapabilityDiscoveryStartedEvent(AgUiEventPayload):
    event_name: Literal["capability_discovery.started"] = "capability_discovery.started"
    requested_skill_ids: tuple[SkillId, ...] = ()


class CapabilityDiscoveryCompletedEvent(AgUiEventPayload):
    event_name: Literal["capability_discovery.completed"] = "capability_discovery.completed"
    discovered_skill_ids: tuple[SkillId, ...] = ()
    missing_skill_ids: tuple[SkillId, ...] = ()


class SpecialistStartedEvent(AgUiEventPayload):
    event_name: Literal["specialist.started"] = "specialist.started"


class SpecialistProgressEvent(AgUiEventPayload):
    event_name: Literal["specialist.progress"] = "specialist.progress"
    message: str = Field(min_length=1)


class SpecialistFindingReceivedEvent(AgUiEventPayload):
    event_name: Literal["specialist.finding_received"] = "specialist.finding_received"
    finding_id: str = Field(min_length=1)


class MissingEvidenceIdentifiedEvent(AgUiEventPayload):
    event_name: Literal["evidence.missing_identified"] = "evidence.missing_identified"
    missing_evidence: tuple[EvidenceType, ...] = ()


class MissingCapabilityIdentifiedEvent(AgUiEventPayload):
    event_name: Literal["capability.missing_identified"] = "capability.missing_identified"
    warning: MissingCapabilityWarning


class PolicyInterpretationReceivedEvent(AgUiEventPayload):
    event_name: Literal["policy.interpretation_received"] = "policy.interpretation_received"


class RecommendationProducedEvent(AgUiEventPayload):
    event_name: Literal["recommendation.produced"] = "recommendation.produced"
    recommendation: RecommendationType


class ExplanationProducedEvent(AgUiEventPayload):
    event_name: Literal["explanation.produced"] = "explanation.produced"
    explanation: str = Field(min_length=1)


class ApprovalRequiredEvent(AgUiEventPayload):
    event_name: Literal["approval.required"] = "approval.required"


class InvestigationCompletedEvent(AgUiEventPayload):
    event_name: Literal["investigation.completed"] = "investigation.completed"
    final_status: str = Field(min_length=1)


class InvestigationFailedEvent(AgUiEventPayload):
    event_name: Literal["investigation.failed"] = "investigation.failed"
    reason: str = Field(min_length=1)
```

- [ ] **Step 2: Write `contracts/tests/test_agui.py`**

```python
"""Tests for chargeback_contracts.agui."""

from datetime import datetime, timezone

from chargeback_contracts.agui import (
    ApprovalRequiredEvent,
    CapabilityDiscoveryCompletedEvent,
    CapabilityDiscoveryStartedEvent,
    ExplanationProducedEvent,
    InvestigationAcceptedEvent,
    InvestigationCompletedEvent,
    InvestigationFailedEvent,
    MissingCapabilityIdentifiedEvent,
    MissingEvidenceIdentifiedEvent,
    PolicyInterpretationReceivedEvent,
    RecommendationProducedEvent,
    SpecialistFindingReceivedEvent,
    SpecialistProgressEvent,
    SpecialistStartedEvent,
)
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId

_CORRELATION = {
    "investigation_id": "INV-1",
    "case_id": "CASE-1",
    "run_id": "RUN-1",
    "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
}


def test_all_fourteen_event_payloads_round_trip_through_json() -> None:
    events = [
        InvestigationAcceptedEvent(
            **_CORRELATION, dispute_type=DisputeType.GOODS_NOT_RECEIVED
        ),
        CapabilityDiscoveryStartedEvent(**_CORRELATION),
        CapabilityDiscoveryCompletedEvent(
            **_CORRELATION, discovered_skill_ids=(SkillId.TRANSACTION_INVESTIGATION,)
        ),
        SpecialistStartedEvent(**_CORRELATION),
        SpecialistProgressEvent(**_CORRELATION, message="Checking transaction records."),
        SpecialistFindingReceivedEvent(**_CORRELATION, finding_id="FIND-1"),
        MissingEvidenceIdentifiedEvent(
            **_CORRELATION, missing_evidence=(EvidenceType.DELIVERY_PROOF,)
        ),
        MissingCapabilityIdentifiedEvent(
            **_CORRELATION,
            warning=MissingCapabilityWarning(
                required_skill_id=SkillId.DUPLICATE_TRANSACTION_INVESTIGATION,
                message="Not registered yet.",
                can_continue_partially=True,
                affected_area="duplicate check",
                discovered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        PolicyInterpretationReceivedEvent(**_CORRELATION),
        RecommendationProducedEvent(
            **_CORRELATION, recommendation=RecommendationType.ACCEPT_CHARGEBACK
        ),
        ExplanationProducedEvent(**_CORRELATION, explanation="Evidence supports the customer."),
        ApprovalRequiredEvent(**_CORRELATION),
        InvestigationCompletedEvent(**_CORRELATION, final_status="completed"),
        InvestigationFailedEvent(**_CORRELATION, reason="specialist timeout"),
    ]
    assert len(events) == 14
    for event in events:
        restored = type(event).model_validate_json(event.model_dump_json())
        assert restored == event


def test_event_name_is_stable_and_distinct_per_event() -> None:
    names = {
        InvestigationAcceptedEvent(
            **_CORRELATION, dispute_type=DisputeType.OTHER
        ).event_name,
        CapabilityDiscoveryStartedEvent(**_CORRELATION).event_name,
        CapabilityDiscoveryCompletedEvent(**_CORRELATION).event_name,
        SpecialistStartedEvent(**_CORRELATION).event_name,
        SpecialistProgressEvent(**_CORRELATION, message="x").event_name,
        SpecialistFindingReceivedEvent(**_CORRELATION, finding_id="F").event_name,
        MissingEvidenceIdentifiedEvent(**_CORRELATION).event_name,
        PolicyInterpretationReceivedEvent(**_CORRELATION).event_name,
        RecommendationProducedEvent(
            **_CORRELATION, recommendation=RecommendationType.REJECT_CHARGEBACK
        ).event_name,
        ExplanationProducedEvent(**_CORRELATION, explanation="x").event_name,
        ApprovalRequiredEvent(**_CORRELATION).event_name,
        InvestigationCompletedEvent(**_CORRELATION, final_status="completed").event_name,
        InvestigationFailedEvent(**_CORRELATION, reason="x").event_name,
    }
    assert len(names) == 13  # MissingCapabilityIdentifiedEvent omitted here for brevity; distinct-name check
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_agui.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/agui.py contracts/tests/test_agui.py
git commit -m "feat: add AG-UI application event payload contracts"
```

---

### Task 10: `a2ui.py` — A2UI decision-interface contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/a2ui.py`
- Create: `contracts/tests/test_a2ui.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.evidence` (`EvidenceRef`, `EvidenceType`), `chargeback_contracts.recommendation` (`RecommendationType`, `MissingCapabilityWarning`).
- Produces: `A2UI_VERSION`, `InvestigatorAction`, `DecisionCard`, `EvidenceChecklist`, `SpecialistFindingsSummary`, `MissingCapabilityWarningPanel`, `RecommendedNextActions`, `ApprovalPreview`, `FinalDecisionConfirmation`, `A2uiEnvelope` — consumed by `decisions.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/a2ui.py`**

```python
"""A2UI application-owned payloads for the investigator decision interface.

No official A2UI SDK exists; every model here is application-owned. The
A2UI specification/protocol version this project targets is exactly
"0.9" — enforced via the Literal type on A2uiEnvelope.version.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType

A2UI_VERSION: Literal["0.9"] = "0.9"


class InvestigatorAction(str, Enum):
    """Human decisions available on the investigator decision interface.

    These represent human decisions, not autonomous agent actions.
    """

    APPROVE_RECOMMENDATION = "approve_recommendation"
    REJECT_RECOMMENDATION = "reject_recommendation"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


class DecisionCard(ContractModel):
    """Distinguishes the deterministic recommendation from its explanation."""

    component_type: Literal["decision_card"] = "decision_card"
    investigation_id: str = Field(min_length=1)
    recommendation: RecommendationType
    explanation: str = Field(min_length=1)
    policy_references: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    has_warnings: bool = False


class EvidenceChecklistItem(ContractModel):
    evidence_type: EvidenceType
    satisfied: bool
    evidence_ref: EvidenceRef | None = None


class EvidenceChecklist(ContractModel):
    component_type: Literal["evidence_checklist"] = "evidence_checklist"
    investigation_id: str = Field(min_length=1)
    items: tuple[EvidenceChecklistItem, ...] = ()


class SpecialistFindingsSummary(ContractModel):
    component_type: Literal["specialist_findings_summary"] = "specialist_findings_summary"
    investigation_id: str = Field(min_length=1)
    finding_summaries: tuple[str, ...] = ()


class MissingCapabilityWarningPanel(ContractModel):
    component_type: Literal["missing_capability_warning_panel"] = (
        "missing_capability_warning_panel"
    )
    investigation_id: str = Field(min_length=1)
    warnings: tuple[MissingCapabilityWarning, ...] = ()


class RecommendedNextAction(ContractModel):
    action: InvestigatorAction
    label: str = Field(min_length=1)


class RecommendedNextActions(ContractModel):
    component_type: Literal["recommended_next_actions"] = "recommended_next_actions"
    investigation_id: str = Field(min_length=1)
    actions: tuple[RecommendedNextAction, ...] = ()


class ApprovalPreview(ContractModel):
    component_type: Literal["approval_preview"] = "approval_preview"
    investigation_id: str = Field(min_length=1)
    recommendation: RecommendationType
    summary: str = Field(min_length=1)


class FinalDecisionConfirmation(ContractModel):
    component_type: Literal["final_decision_confirmation"] = "final_decision_confirmation"
    investigation_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    action: InvestigatorAction
    confirmed_at: datetime

    @field_validator("confirmed_at")
    @classmethod
    def _confirmed_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="confirmed_at")


A2uiComponent = Annotated[
    Union[
        DecisionCard,
        EvidenceChecklist,
        SpecialistFindingsSummary,
        MissingCapabilityWarningPanel,
        RecommendedNextActions,
        ApprovalPreview,
        FinalDecisionConfirmation,
    ],
    Field(discriminator="component_type"),
]


class A2uiEnvelope(ContractModel):
    """Envelope wrapping the components rendered on the decision interface."""

    version: Literal["0.9"]
    surface_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    components: tuple[A2uiComponent, ...] = ()
    allowed_actions: tuple[InvestigatorAction, ...] = ()
    generated_at: datetime

    @field_validator("surface_id", "investigation_id")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("generated_at")
    @classmethod
    def _generated_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="generated_at")
```

- [ ] **Step 2: Write `contracts/tests/test_a2ui.py`**

```python
"""Tests for chargeback_contracts.a2ui."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import (
    A2UI_VERSION,
    A2uiEnvelope,
    ApprovalPreview,
    DecisionCard,
    FinalDecisionConfirmation,
    InvestigatorAction,
)
from chargeback_contracts.recommendation import RecommendationType


def _valid_envelope(**overrides: object) -> A2uiEnvelope:
    defaults: dict[str, object] = {
        "version": A2UI_VERSION,
        "surface_id": "decision-surface-1",
        "investigation_id": "INV-1",
        "components": (
            DecisionCard(
                investigation_id="INV-1",
                recommendation=RecommendationType.ACCEPT_CHARGEBACK,
                explanation="Evidence supports acceptance.",
            ),
        ),
        "allowed_actions": (InvestigatorAction.APPROVE_RECOMMENDATION,),
        "generated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return A2uiEnvelope(**defaults)  # type: ignore[arg-type]


def test_valid_envelope_round_trips_through_json() -> None:
    envelope = _valid_envelope()
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert restored == envelope
    assert type(restored.components[0]) is DecisionCard


def test_version_must_be_exactly_0_9() -> None:
    with pytest.raises(ValidationError):
        _valid_envelope(version="1.0")


def test_allowed_actions_are_human_decisions_only() -> None:
    envelope = _valid_envelope()
    assert all(isinstance(a, InvestigatorAction) for a in envelope.allowed_actions)


def test_discriminated_components_round_trip_for_final_decision_confirmation() -> None:
    envelope = _valid_envelope(
        components=(
            FinalDecisionConfirmation(
                investigation_id="INV-1",
                decision_id="DEC-1",
                action=InvestigatorAction.APPROVE_RECOMMENDATION,
                confirmed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        )
    )
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert type(restored.components[0]) is FinalDecisionConfirmation


def test_discriminated_components_round_trip_for_approval_preview() -> None:
    envelope = _valid_envelope(
        components=(
            ApprovalPreview(
                investigation_id="INV-1",
                recommendation=RecommendationType.REJECT_CHARGEBACK,
                summary="Policy does not support this claim.",
            ),
        )
    )
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert type(restored.components[0]) is ApprovalPreview


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_envelope(unexpected_field="nope")
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_a2ui.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/a2ui.py contracts/tests/test_a2ui.py
git commit -m "feat: add A2UI decision-interface contracts (version 0.9)"
```

---

### Task 11: `decisions.py` — human-decision contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/decisions.py`
- Create: `contracts/tests/test_decisions.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.a2ui` (`InvestigatorAction`), `chargeback_contracts.recommendation` (`RecommendationType`).
- Produces: `InvestigatorDecision` — consumed by `mcp.py` (referenced for the audit write contract) and `records.py`.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/decisions.py`**

```python
"""Human-decision contracts.

No write-side MCP command may be represented as approved without an
InvestigatorDecision — this module is what makes human approval
explicit and mandatory rather than implied.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.recommendation import RecommendationType


class InvestigatorDecision(ContractModel):
    """A recorded human decision on an investigation's recommendation."""

    decision_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    investigator_id: str = Field(min_length=1)
    selected_action: InvestigatorAction
    comments: str | None = None
    recommendation_shown: RecommendationType
    decided_at: datetime
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator("decision_id", "investigation_id", "case_id", "investigator_id")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("decided_at")
    @classmethod
    def _decided_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="decided_at")

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: object) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]
        return value
```

- [ ] **Step 2: Write `contracts/tests/test_decisions.py`**

```python
"""Tests for chargeback_contracts.decisions."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.recommendation import RecommendationType


def _valid_decision(**overrides: object) -> InvestigatorDecision:
    defaults: dict[str, object] = {
        "decision_id": "DEC-1",
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "investigator_id": "inv-jane",
        "selected_action": InvestigatorAction.APPROVE_RECOMMENDATION,
        "recommendation_shown": RecommendationType.ACCEPT_CHARGEBACK,
        "decided_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return InvestigatorDecision(**defaults)  # type: ignore[arg-type]


def test_valid_decision_round_trips_through_json() -> None:
    decision = _valid_decision()
    restored = InvestigatorDecision.model_validate_json(decision.model_dump_json())
    assert restored == decision


def test_requires_explicit_investigator_id() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(investigator_id="   ")


def test_requires_decision_timestamp() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(decided_at=None)


def test_rejects_naive_decided_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_decision(decided_at=datetime(2026, 1, 1))  # noqa: DTZ001


def test_comments_are_optional() -> None:
    decision = _valid_decision()
    assert decision.comments is None


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(unexpected_field="nope")
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_decisions.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/decisions.py contracts/tests/test_decisions.py
git commit -m "feat: add investigator decision contract"
```

---

### Task 12: `mcp.py` — MCP boundary contracts

**Files:**
- Create: `contracts/src/chargeback_contracts/mcp.py`
- Create: `contracts/tests/test_mcp.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.evidence` (`EvidenceRef`, `EvidenceType`), `chargeback_contracts.findings` (`CustomerHistoryFindingDetails`), `chargeback_contracts.decisions` (`InvestigatorDecision`).
- Produces: read/write request/response models — consumed by nothing else in this plan (leaf-ward).

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/mcp.py`**

```python
"""MCP boundary contracts for the future mock MCP tool groups.

Application-owned request/response shapes only — this module does not
implement MCP tools or clients, and stays separate from the official MCP
protocol implementation.

`get_case` / `get_transaction` intentionally stay minimal: no case or
transaction business record schema exists anywhere in this contract layer
(inventing one would be a mock business service, out of scope for this
prompt) — the real shape is owned by the prompt that implements
dispute-mcp-server. `get_customer_history` and `get_merchant_evidence` /
`list_case_documents` reuse the already-defined
`CustomerHistoryFindingDetails` and `EvidenceRef` shapes, since a specialist
finding and an MCP read of the same domain data should look the same.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.findings import CustomerHistoryFindingDetails


class McpStatus(str, Enum):
    """Success/failure status for an MCP-facing operation."""

    SUCCESS = "success"
    FAILURE = "failure"


class McpErrorInfo(ContractModel):
    error_code: str = Field(min_length=1)
    safe_message: str = Field(min_length=1)


# --- Read-side ---


class GetCaseRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetCaseResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    found: bool
    error: McpErrorInfo | None = None


class GetTransactionRequest(ContractModel):
    transaction_id: str = Field(min_length=1)


class GetTransactionResponse(ContractModel):
    status: McpStatus
    transaction_id: str = Field(min_length=1)
    found: bool
    error: McpErrorInfo | None = None


class GetCustomerHistoryRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetCustomerHistoryResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    result: CustomerHistoryFindingDetails | None = None
    error: McpErrorInfo | None = None


class GetMerchantEvidenceRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetMerchantEvidenceResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    evidence_refs: tuple[EvidenceRef, ...] = ()
    error: McpErrorInfo | None = None


class ListCaseDocumentsRequest(ContractModel):
    case_id: str = Field(min_length=1)


class ListCaseDocumentsResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    documents: tuple[EvidenceRef, ...] = ()
    error: McpErrorInfo | None = None


# --- Write-side ---


class McpWriteRequestBase(ContractModel):
    """Every write-side MCP request must carry an idempotency key."""

    case_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)

    @field_validator("idempotency_key")
    @classmethod
    def _non_blank_idempotency_key(cls, value: str) -> str:
        return require_non_blank(value, field_name="idempotency_key")


class CreateEvidenceRequestTaskRequest(McpWriteRequestBase):
    requested_evidence_types: tuple[EvidenceType, ...] = ()
    message_to_customer: str = Field(min_length=1)


class UpdateCaseStatusRequest(McpWriteRequestBase):
    new_status: str = Field(min_length=1)


class CreateAuditEntryRequest(McpWriteRequestBase):
    investigator_decision: InvestigatorDecision | None = None
    event_description: str = Field(min_length=1)


class McpWriteResponse(ContractModel):
    status: McpStatus
    audit_correlation_id: str = Field(min_length=1)
    error: McpErrorInfo | None = None
```

- [ ] **Step 2: Write `contracts/tests/test_mcp.py`**

```python
"""Tests for chargeback_contracts.mcp."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.findings import CustomerHistoryFindingDetails
from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    CreateEvidenceRequestTaskRequest,
    GetCaseResponse,
    GetCustomerHistoryResponse,
    McpStatus,
    McpWriteResponse,
    UpdateCaseStatusRequest,
)
from chargeback_contracts.recommendation import RecommendationType


def test_get_case_response_round_trips_through_json() -> None:
    response = GetCaseResponse(status=McpStatus.SUCCESS, case_id="CASE-1", found=True)
    restored = GetCaseResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_get_customer_history_response_reuses_finding_details_shape() -> None:
    response = GetCustomerHistoryResponse(
        status=McpStatus.SUCCESS,
        case_id="CASE-1",
        result=CustomerHistoryFindingDetails(previous_dispute_count=1, previous_refund_count=0),
    )
    restored = GetCustomerHistoryResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_write_request_requires_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        UpdateCaseStatusRequest(case_id="CASE-1", idempotency_key="", new_status="closed")


def test_write_request_rejects_blank_idempotency_key() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        UpdateCaseStatusRequest(case_id="CASE-1", idempotency_key="   ", new_status="closed")


def test_create_audit_entry_can_carry_investigator_decision() -> None:
    decision = InvestigatorDecision(
        decision_id="DEC-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        investigator_id="inv-jane",
        selected_action=InvestigatorAction.APPROVE_RECOMMENDATION,
        recommendation_shown=RecommendationType.ACCEPT_CHARGEBACK,
        decided_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    request = CreateAuditEntryRequest(
        case_id="CASE-1",
        idempotency_key="idem-1",
        investigator_decision=decision,
        event_description="Investigator approved the recommendation.",
    )
    restored = CreateAuditEntryRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_write_response_round_trips_through_json() -> None:
    response = McpWriteResponse(status=McpStatus.SUCCESS, audit_correlation_id="AUD-1")
    restored = McpWriteResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_evidence_request_task_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        CreateEvidenceRequestTaskRequest(
            case_id="CASE-1",
            idempotency_key="idem-1",
            message_to_customer="Please provide delivery proof.",
            unexpected_field="nope",
        )
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_mcp.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/mcp.py contracts/tests/test_mcp.py
git commit -m "feat: add MCP boundary request/response contracts"
```

---

### Task 13: `records.py` — investigation record

**Files:**
- Create: `contracts/src/chargeback_contracts/records.py`
- Create: `contracts/tests/test_records.py`

**Interfaces:**
- Consumes: `chargeback_contracts.common`, `chargeback_contracts.dispute` (`InvestigationRequest`), `chargeback_contracts.skills` (`SkillId`), `chargeback_contracts.findings` (`SpecialistFinding`), `chargeback_contracts.policy` (`PolicyInterpretation`), `chargeback_contracts.recommendation` (`InvestigationRecommendation`, `MissingCapabilityWarning`), `chargeback_contracts.decisions` (`InvestigatorDecision`).
- Produces: `WorkflowStatus`, `InvestigationRecord` — the DAG's root; nothing else imports it.

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/records.py`**

```python
"""Final investigation record, suitable for audit persistence.

A completed InvestigationRecord requires an InvestigatorDecision — this is
what makes mandatory human approval structurally enforced rather than a
convention. A partial or failed investigation may exist without a final
decision, but its status must accurately reflect that state.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.dispute import InvestigationRequest
from chargeback_contracts.findings import SpecialistFinding
from chargeback_contracts.policy import PolicyInterpretation
from chargeback_contracts.recommendation import InvestigationRecommendation, MissingCapabilityWarning
from chargeback_contracts.skills import SkillId


class WorkflowStatus(str, Enum):
    """The investigation's overall workflow state."""

    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationRecord(ContractModel):
    """The durable record of one chargeback investigation, for audit persistence.

    `recommendation.explanation` is the explanation generated alongside the
    deterministic recommendation; the top-level `explanation` field is the
    current explanation surfaced to the investigator and may be
    independently regenerated (e.g. by an LLM) without touching the
    immutable deterministic recommendation fields.
    """

    request: InvestigationRequest
    discovered_skill_ids: tuple[SkillId, ...] = ()
    missing_capability_warnings: tuple[MissingCapabilityWarning, ...] = ()
    specialist_findings: tuple[SpecialistFinding, ...] = ()
    policy_interpretation: PolicyInterpretation | None = None
    recommendation: InvestigationRecommendation | None = None
    explanation: str | None = None
    investigator_decision: InvestigatorDecision | None = None
    created_at: datetime
    completed_at: datetime | None = None
    status: WorkflowStatus
    audit_correlation_id: str = Field(min_length=1)

    @field_validator("created_at")
    @classmethod
    def _created_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="created_at")

    @field_validator("completed_at")
    @classmethod
    def _completed_at(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return require_utc(value, field_name="completed_at")
        return value

    @model_validator(mode="after")
    def _validate_workflow_rules(self) -> "InvestigationRecord":
        if self.status == WorkflowStatus.COMPLETED and self.investigator_decision is None:
            raise ValueError(
                "a completed InvestigationRecord requires an InvestigatorDecision"
            )
        if (
            self.completed_at is not None
            and self.completed_at < self.created_at
        ):
            raise ValueError("completed_at cannot precede created_at")
        return self
```

- [ ] **Step 2: Write `contracts/tests/test_records.py`**

```python
"""Tests for chargeback_contracts.records."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.dispute import InvestigationRequest, SourceChannel
from chargeback_contracts.recommendation import RecommendationType
from chargeback_contracts.records import InvestigationRecord, WorkflowStatus
from chargeback_contracts.skills import DisputeType


def _base_request() -> InvestigationRequest:
    return InvestigationRequest(
        investigation_id="INV-1",
        case_id="CASE-1",
        transaction_id="TXN-1",
        source_channel=SourceChannel.WEB_FORM,
        customer_narrative="Item never arrived.",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        amount=Decimal("50.00"),
        currency="USD",
        submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _decision() -> InvestigatorDecision:
    return InvestigatorDecision(
        decision_id="DEC-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        investigator_id="inv-jane",
        selected_action=InvestigatorAction.APPROVE_RECOMMENDATION,
        recommendation_shown=RecommendationType.ACCEPT_CHARGEBACK,
        decided_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )


def test_completed_record_requires_investigator_decision() -> None:
    with pytest.raises(ValidationError, match="requires an InvestigatorDecision"):
        InvestigationRecord(
            request=_base_request(),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            status=WorkflowStatus.COMPLETED,
            audit_correlation_id="AUD-1",
        )


def test_completed_record_with_decision_is_valid_and_round_trips() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        investigator_decision=_decision(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        status=WorkflowStatus.COMPLETED,
        audit_correlation_id="AUD-1",
    )
    restored = InvestigationRecord.model_validate_json(record.model_dump_json())
    assert restored == record


def test_partial_record_without_decision_is_valid() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=WorkflowStatus.PARTIAL,
        audit_correlation_id="AUD-1",
    )
    assert record.investigator_decision is None
    assert record.status == WorkflowStatus.PARTIAL


def test_failed_record_without_decision_is_valid() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=WorkflowStatus.FAILED,
        audit_correlation_id="AUD-1",
    )
    assert record.status == WorkflowStatus.FAILED


def test_completed_at_cannot_precede_created_at() -> None:
    with pytest.raises(ValidationError, match="cannot precede created_at"):
        InvestigationRecord(
            request=_base_request(),
            investigator_decision=_decision(),
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=WorkflowStatus.COMPLETED,
            audit_correlation_id="AUD-1",
        )


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        InvestigationRecord(
            request=_base_request(),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=WorkflowStatus.IN_PROGRESS,
            audit_correlation_id="AUD-1",
            unexpected_field="nope",
        )
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_records.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add contracts/src/chargeback_contracts/records.py contracts/tests/test_records.py
git commit -m "feat: add investigation record contract with mandatory-approval validation"
```

---

### Task 14: `__init__.py` public surface + workspace-wide import test

**Files:**
- Modify: `contracts/src/chargeback_contracts/__init__.py`
- Create: `contracts/tests/test_public_surface.py`

**Interfaces:**
- Consumes: every module created in Tasks 2–13.
- Produces: the package's public contract surface (test requirement #1 and #19 verification point).

- [ ] **Step 1: Write `contracts/src/chargeback_contracts/__init__.py`**

```python
"""Shared, strongly-typed contract layer for the chargeback investigation platform.

Every application-owned payload that crosses a service boundary (A2A,
Agent Registry, AG-UI, A2UI, MCP-facing adapters, audit persistence) is
defined here. This package has zero imports from any other application
package — every other service depends inward on `chargeback_contracts`.

Official protocol types are never redefined here: A2A objects come from
`a2a.types` (protobuf-backed in a2a-sdk 1.1.1 — this package only carries
their string `task_id`/`context_id` identifiers), and AG-UI's official
event envelope comes from `ag_ui.core.CustomEvent` (this package defines
only the typed `value` payloads for it).
"""

from __future__ import annotations

__version__ = "0.1.0"

from chargeback_contracts.a2ui import (
    A2UI_VERSION,
    A2uiComponent,
    A2uiEnvelope,
    ApprovalPreview,
    DecisionCard,
    EvidenceChecklist,
    EvidenceChecklistItem,
    FinalDecisionConfirmation,
    InvestigatorAction,
    MissingCapabilityWarningPanel,
    RecommendedNextAction,
    RecommendedNextActions,
    SpecialistFindingsSummary,
)
from chargeback_contracts.agui import (
    AgUiEventPayload,
    ApprovalRequiredEvent,
    CapabilityDiscoveryCompletedEvent,
    CapabilityDiscoveryStartedEvent,
    ExplanationProducedEvent,
    InvestigationAcceptedEvent,
    InvestigationCompletedEvent,
    InvestigationFailedEvent,
    MissingCapabilityIdentifiedEvent,
    MissingEvidenceIdentifiedEvent,
    PolicyInterpretationReceivedEvent,
    RecommendationProducedEvent,
    SpecialistFindingReceivedEvent,
    SpecialistProgressEvent,
    SpecialistStartedEvent,
)
from chargeback_contracts.common import ContractModel
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.dispute import InvestigationRequest, SourceChannel
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.findings import (
    CustomerHistoryFindingDetails,
    FindingDetails,
    FindingStatus,
    MerchantEvidenceFindingDetails,
    SpecialistFinding,
    TransactionFindingDetails,
)
from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    CreateEvidenceRequestTaskRequest,
    GetCaseRequest,
    GetCaseResponse,
    GetCustomerHistoryRequest,
    GetCustomerHistoryResponse,
    GetMerchantEvidenceRequest,
    GetMerchantEvidenceResponse,
    GetTransactionRequest,
    GetTransactionResponse,
    ListCaseDocumentsRequest,
    ListCaseDocumentsResponse,
    McpErrorInfo,
    McpStatus,
    McpWriteRequestBase,
    McpWriteResponse,
    UpdateCaseStatusRequest,
)
from chargeback_contracts.policy import PolicyInterpretation
from chargeback_contracts.recommendation import (
    InvestigationRecommendation,
    MissingCapabilityWarning,
    RecommendationType,
)
from chargeback_contracts.records import InvestigationRecord, WorkflowStatus
from chargeback_contracts.skills import (
    CORE_EVIDENCE_SKILL_IDS,
    DUPLICATE_TRANSACTION_SKILL_ID,
    POLICY_SKILL_ID,
    DisputeType,
    SkillId,
    required_skills_for,
)

__all__ = [
    "A2UI_VERSION",
    "A2uiComponent",
    "A2uiEnvelope",
    "AgUiEventPayload",
    "ApprovalPreview",
    "ApprovalRequiredEvent",
    "CORE_EVIDENCE_SKILL_IDS",
    "CapabilityDiscoveryCompletedEvent",
    "CapabilityDiscoveryStartedEvent",
    "ContractModel",
    "CreateAuditEntryRequest",
    "CreateEvidenceRequestTaskRequest",
    "CustomerHistoryFindingDetails",
    "DUPLICATE_TRANSACTION_SKILL_ID",
    "DecisionCard",
    "DisputeType",
    "EvidenceChecklist",
    "EvidenceChecklistItem",
    "EvidenceRef",
    "EvidenceType",
    "ExplanationProducedEvent",
    "FinalDecisionConfirmation",
    "FindingDetails",
    "FindingStatus",
    "GetCaseRequest",
    "GetCaseResponse",
    "GetCustomerHistoryRequest",
    "GetCustomerHistoryResponse",
    "GetMerchantEvidenceRequest",
    "GetMerchantEvidenceResponse",
    "GetTransactionRequest",
    "GetTransactionResponse",
    "InvestigationAcceptedEvent",
    "InvestigationCompletedEvent",
    "InvestigationFailedEvent",
    "InvestigationRecommendation",
    "InvestigationRecord",
    "InvestigationRequest",
    "InvestigatorAction",
    "InvestigatorDecision",
    "ListCaseDocumentsRequest",
    "ListCaseDocumentsResponse",
    "McpErrorInfo",
    "McpStatus",
    "McpWriteRequestBase",
    "McpWriteResponse",
    "MerchantEvidenceFindingDetails",
    "MissingCapabilityIdentifiedEvent",
    "MissingCapabilityWarning",
    "MissingCapabilityWarningPanel",
    "MissingEvidenceIdentifiedEvent",
    "POLICY_SKILL_ID",
    "PolicyInterpretation",
    "PolicyInterpretationReceivedEvent",
    "RecommendationProducedEvent",
    "RecommendationType",
    "RecommendedNextAction",
    "RecommendedNextActions",
    "SkillId",
    "SourceChannel",
    "SpecialistFinding",
    "SpecialistFindingReceivedEvent",
    "SpecialistFindingsSummary",
    "SpecialistProgressEvent",
    "SpecialistStartedEvent",
    "TransactionFindingDetails",
    "UpdateCaseStatusRequest",
    "WorkflowStatus",
    "__version__",
    "required_skills_for",
]
```

- [ ] **Step 2: Write `contracts/tests/test_public_surface.py`**

```python
"""Tests for the chargeback_contracts public import surface."""

import chargeback_contracts as contracts


def test_module_imports() -> None:
    assert contracts is not None


def test_every_declared_export_is_actually_importable() -> None:
    for name in contracts.__all__:
        assert hasattr(contracts, name), f"{name} is declared in __all__ but missing"


def test_no_duplicate_a2a_protocol_model_names_defined_locally() -> None:
    reserved_a2a_names = {
        "AgentCard",
        "AgentSkill",
        "Task",
        "Message",
        "Artifact",
        "Part",
        "TaskState",
    }
    assert reserved_a2a_names.isdisjoint(contracts.__all__)


def test_key_contracts_importable_from_package_root() -> None:
    assert contracts.InvestigationRequest is not None
    assert contracts.SpecialistFinding is not None
    assert contracts.PolicyInterpretation is not None
    assert contracts.InvestigationRecommendation is not None
    assert contracts.InvestigatorDecision is not None
    assert contracts.InvestigationRecord is not None
    assert contracts.A2uiEnvelope is not None
    assert contracts.A2UI_VERSION == "0.9"
```

- [ ] **Step 3: Run the focused test**

Run: `uv run pytest contracts/tests/test_public_surface.py -v`
Expected: all tests pass.

- [ ] **Step 4: Run the full contracts suite**

Run: `uv run pytest contracts/ -v`
Expected: every test file created in Tasks 2–14 passes (no import errors, no circular-import errors).

- [ ] **Step 5: Commit**

```bash
git add contracts/src/chargeback_contracts/__init__.py contracts/tests/test_public_surface.py
git commit -m "feat: expose contracts public surface from package root"
```

---

### Task 15: Narrow the mypy `tests/` exclusion; strict-check contracts

**Files:**
- Modify: `pyproject.toml` (repo root)

**Interfaces:**
- Consumes: the `[tool.mypy]` section Prompt 1 added.
- Produces: strict mypy coverage for `contracts/` (production and test code) while the other 9 packages' trivial smoke tests stay excluded exactly as before.

- [ ] **Step 1: Read the current `[tool.mypy]` section**

It currently contains (from Prompt 1, Task 3's fix):
```toml
[tool.mypy]
python_version = "3.13"
strict = true
warn_unused_ignores = true
namespace_packages = true
explicit_package_bases = true
mypy_path = [ ... 10 package src/ paths ... ]
exclude = ["(^|/)tests/"]
```

- [ ] **Step 2: Narrow the `exclude` pattern**

Replace the blanket `exclude = ["(^|/)tests/"]` with a pattern naming only
the 9 packages that still have nothing but a trivial import-smoke test
(everything except `contracts`):

```toml
exclude = [
    "^orchestrator-agent/tests/",
    "^transaction-agent/tests/",
    "^customer-history-agent/tests/",
    "^merchant-evidence-agent/tests/",
    "^policy-agent/tests/",
    "^duplicate-transaction-agent/tests/",
    "^agent-registry/tests/",
    "^dispute-mcp-server/tests/",
    "^knowledge-ingestor/tests/",
]
```

Add a comment directly above the `exclude` key explaining why (per the
user's explicit request to document this as temporary technical debt):

```toml
# Temporary technical debt (introduced in Prompt 1, narrowed in Prompt 2):
# these 9 packages still have only a single import-smoke `tests/test_import.py`
# with no `__init__.py`, so mypy's duplicate-module-name detector would
# otherwise refuse to run (all 9 files share the bare module name
# `test_import`). `contracts/tests/` is intentionally NOT excluded — it now
# has real test logic and must be strict-mypy-checked like production code.
# Remove each package's line below once that package gains real tests (or
# at minimum a `tests/__init__.py`), one line at a time, rather than in one
# batch — do not remove this comment until the list is empty.
exclude = [
    "^orchestrator-agent/tests/",
    "^transaction-agent/tests/",
    "^customer-history-agent/tests/",
    "^merchant-evidence-agent/tests/",
    "^policy-agent/tests/",
    "^duplicate-transaction-agent/tests/",
    "^agent-registry/tests/",
    "^dispute-mcp-server/tests/",
    "^knowledge-ingestor/tests/",
]
```

- [ ] **Step 3: Run mypy**

Run: `uv run mypy .`
Expected: `contracts/src/` and `contracts/tests/` are now type-checked under `strict = true`. Fix any real error mypy reports in the specific file it points to — do not add blanket `# type: ignore` comments; if a `field_validator`'s `info: object` parameter (used throughout Tasks 4–13) causes a real mypy error on `info.field_name`, replace the parameter's annotation with `pydantic.ValidationInfo` (the correct type) in every file that uses this pattern and remove the `# type: ignore[attr-defined]` hedge comments — this was flagged as a known follow-up in Task 4's Step 2, and this is the task where it gets resolved for real, once, based on the actual mypy output rather than guessed in advance.

- [ ] **Step 4: If the `ValidationInfo` fix is needed, apply it uniformly**

If Step 3 shows the hedge was necessary, update every `field_validator` classmethod across `common.py`, `evidence.py`, `dispute.py`, `findings.py`, `policy.py`, `recommendation.py`, `agui.py`, `a2ui.py`, `decisions.py`, `mcp.py`, `records.py` that used `info: object` to instead use `info: ValidationInfo` (importing `from pydantic import ValidationInfo` in each file that needs it), and delete the now-unnecessary `# type: ignore[attr-defined]` comments. Re-run `uv run mypy .` until clean.

- [ ] **Step 5: Run the full contracts test suite once more**

Run: `uv run pytest contracts/ -v`
Expected: still all passing (Step 4's changes are type-annotation-only, no behavior change).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml contracts/src/chargeback_contracts/*.py
git commit -m "fix: narrow mypy tests exclusion to the 9 packages without real tests yet"
```

(If Step 4 wasn't needed, this commit only touches `pyproject.toml` — adjust the `git add` accordingly.)

---

### Task 16: Wire `contracts` into `orchestrator-agent` and `transaction-agent`

**Files:**
- Modify: `orchestrator-agent/pyproject.toml`
- Create: `orchestrator-agent/tests/test_contracts_integration.py`
- Modify: `transaction-agent/pyproject.toml`
- Create: `transaction-agent/tests/test_contracts_integration.py`

**Interfaces:**
- Consumes: `chargeback_contracts.InvestigationRequest` (or another simple contract).
- Produces: test requirement #20 ("workspace imports from at least two dependent packages").

**No business logic is added to either package** — this is strictly a dependency declaration plus one proof-of-wiring test per package.

- [ ] **Step 1: Update `orchestrator-agent/pyproject.toml`**

Current (from Prompt 1):
```toml
[project]
name = "orchestrator-agent"
version = "0.1.0"
description = "Coordinates investigations and deterministic aggregation"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/orchestrator_agent"]
```

Add the workspace dependency:
```toml
[project]
name = "orchestrator-agent"
version = "0.1.0"
description = "Coordinates investigations and deterministic aggregation"
requires-python = ">=3.13"
dependencies = ["contracts"]

[tool.uv.sources]
contracts = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/orchestrator_agent"]
```

- [ ] **Step 2: Write `orchestrator-agent/tests/test_contracts_integration.py`**

```python
"""Proves orchestrator-agent can consume the shared contracts package."""

from datetime import datetime, timezone
from decimal import Decimal

from chargeback_contracts import DisputeType, InvestigationRequest, SourceChannel


def test_can_construct_and_round_trip_an_investigation_request() -> None:
    request = InvestigationRequest(
        investigation_id="INV-1",
        case_id="CASE-1",
        transaction_id="TXN-1",
        source_channel=SourceChannel.WEB_FORM,
        customer_narrative="Item never arrived.",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        amount=Decimal("25.00"),
        currency="USD",
        submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    restored = InvestigationRequest.model_validate_json(request.model_dump_json())
    assert restored == request
```

- [ ] **Step 3: Update `transaction-agent/pyproject.toml`**

Same pattern:
```toml
[project]
name = "transaction-agent"
version = "0.1.0"
description = "Transaction-domain investigation"
requires-python = ">=3.13"
dependencies = ["contracts"]

[tool.uv.sources]
contracts = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/transaction_agent"]
```

- [ ] **Step 4: Write `transaction-agent/tests/test_contracts_integration.py`**

```python
"""Proves transaction-agent can consume the shared contracts package."""

from datetime import datetime, timezone

from chargeback_contracts import (
    FindingStatus,
    SkillId,
    SpecialistFinding,
    TransactionFindingDetails,
)


def test_can_construct_and_round_trip_a_transaction_finding() -> None:
    finding = SpecialistFinding(
        finding_id="FIND-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        producing_agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
        status=FindingStatus.COMPLETED,
        summary="Transaction confirmed as posted.",
        details=TransactionFindingDetails(transaction_matched=True),
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
    )
    restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
    assert restored == finding
```

- [ ] **Step 5: Re-lock and sync the workspace**

Run: `uv lock && uv sync --all-packages`
Expected: resolves cleanly, with `orchestrator-agent` and `transaction-agent` now depending on the workspace-local `contracts` package.

- [ ] **Step 6: Run the two new integration tests**

Run: `uv run pytest orchestrator-agent/tests/test_contracts_integration.py transaction-agent/tests/test_contracts_integration.py -v`
Expected: both pass.

- [ ] **Step 7: Run the full pytest suite**

Run: `uv run pytest`
Expected: all tests across all 10 packages pass (the original 8 untouched packages' smoke tests, plus contracts' full suite, plus these 2 new integration tests).

- [ ] **Step 8: Commit**

```bash
git add orchestrator-agent/pyproject.toml orchestrator-agent/tests/test_contracts_integration.py transaction-agent/pyproject.toml transaction-agent/tests/test_contracts_integration.py uv.lock
git commit -m "test: wire contracts into orchestrator-agent and transaction-agent"
```

---

### Task 17: README contract overview

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing (documentation only).

- [ ] **Step 1: Add a "Shared Contract Layer" section to `README.md`**

Insert this new section directly after the existing "Module responsibilities" table (keep everything else in the README unchanged):

```markdown
## Shared contract layer

Every stable payload that crosses a service boundary — A2A (Orchestrator ↔
specialists), Agent Registry ↔ agents, AG-UI (Orchestrator ↔ UI), A2UI
(Orchestrator ↔ investigator decision surface), MCP-facing adapters, and
audit persistence — is defined once in `contracts` (import name
`chargeback_contracts`). All application services depend inward on it; it
depends on nothing in this repository.

```text
orchestrator-agent  transaction-agent  customer-history-agent  ...
        \                  |                    /
         \                 |                   /
          \                |                  /
           v                v                v
                    chargeback_contracts
```

Key points:

- Official A2A protocol objects (`Task`, `Message`, `AgentSkill`, ...) come
  from `a2a.types` (`a2a-sdk`) — this repository never redefines them; it
  only carries their string `task_id` / `context_id` identifiers.
- Official AG-UI event types come from `ag_ui.core` (`ag-ui-protocol`);
  `chargeback_contracts` defines only the typed application payloads
  carried inside a `CustomEvent`.
- A2UI has no official SDK; every A2UI payload here is application-owned,
  targeting specification version `0.9`.
- Specialists (`SpecialistFinding`) and the Policy Agent
  (`PolicyInterpretation`) never carry a recommendation — only
  `InvestigationRecommendation` does, and it is always deterministic;
  `explanation` is independent, descriptive text.
- Human approval is mandatory: a `WorkflowStatus.COMPLETED`
  `InvestigationRecord` cannot validate without an `InvestigatorDecision`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add shared contract layer overview to README"
```

---

### Task 18: Full verification run

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 1–17.

- [ ] **Step 1: Run `make verify` from the repo root**

Run: `make verify`
Expected: Ruff format-check passes, Ruff lint passes, strict Mypy passes (production and, for `contracts`, test code), the full pytest suite passes (10 original package smoke tests minus the deleted `contracts/tests/test_import.py`, plus the full `contracts` suite, plus 2 new integration tests), and the `investigator-ui` build still succeeds unchanged.

- [ ] **Step 2: If anything fails**

Fix the specific file the error points to. Do not weaken Ruff's `select` list, Mypy's `strict = true`, or TypeScript's `strict`. Re-run `make verify` until clean. Commit each fix separately with a clear, specific message.

- [ ] **Step 3: Confirm working tree is clean**

Run: `git status --short`
Expected: no output from this batch's own changes (the pre-existing, already-committed `.gitignore`/`tmp/` state from before this prompt is untouched and shows nothing new).

---

### Task 19: Consolidated changelog commit

**Files:**
- Modify: `docs/COMMIT_LOG.md`

**Interfaces:**
- Consumes: the full commit history produced by Tasks 1–18.

Per the user's explicit instruction: the changelog is written and
committed **once**, covering every individual commit made in Tasks 1–18 —
not per-commit. Given the Prompt 1 incident where a fresh implementer
subagent mistakenly wrote premature entries mid-batch, **this task should
be performed directly by the controller**, not delegated to a fresh
subagent, exactly as was done at the end of Prompt 1.

- [ ] **Step 1: List this batch's commits for reference**

Run: `git log --oneline <task-1-base-sha>..HEAD`
(the base SHA is the commit immediately before Task 1 started — recorded
in the progress ledger when this plan begins execution).

- [ ] **Step 2: Prepend entries to `docs/COMMIT_LOG.md`**

Add one entry per logical unit of work (contracts dependencies; common.py;
skills.py; evidence.py; dispute.py; findings.py; policy.py;
recommendation.py; agui.py; a2ui.py; decisions.py; mcp.py; records.py;
public surface; mypy exclusion narrowing; orchestrator-agent/
transaction-agent wiring; README; any fix commits from Task 18), most
recent first, above the existing top entry. Use today's actual date and
the real filenames touched.

- [ ] **Step 3: Commit**

```bash
git add docs/COMMIT_LOG.md
git commit -m "docs: log Prompt 2 shared contract layer batch"
```

---

## Self-Review Notes

- **Spec coverage:** all 12 numbered contract sections map to a task
  (skills → Task 3; dispute intake → Task 5; evidence → Task 4; specialist
  findings → Task 6; policy → Task 7; missing-capability + recommendation →
  Task 8; AG-UI → Task 9; A2UI → Task 10; human-decision → Task 11; MCP
  boundary → Task 12; investigation record → Task 13); public surface →
  Task 14; mypy cleanup → Task 15; workspace-dependency test requirement →
  Task 16; README/COMMIT_LOG → Tasks 17/19; full verification → Task 18.
- **No placeholders:** every step has complete, real code — the one
  explicit hedge (`info: object` / `ValidationInfo`) is resolved for real
  in Task 15 based on actual mypy output, not left unresolved.
- **Type/name consistency:** `SkillId`, `DisputeType`, `EvidenceType`,
  `FindingStatus`, `RecommendationType`, `InvestigatorAction`,
  `WorkflowStatus`, `McpStatus` are each defined exactly once and imported
  by name everywhere they're used across Tasks 5–16.
- **No duplicate A2A models:** verified structurally (no class in any
  module is named `AgentCard`/`AgentSkill`/`Task`/`Message`/`Artifact`/
  `Part`/`TaskState`) and by an explicit test in Task 14.
- **Deferred backend deps from Prompt 1 remain deferred** except for the
  three this prompt explicitly introduces (`pydantic`, `a2a-sdk`,
  `ag-ui-protocol`) into `contracts` only — no other package's
  dependencies change in this plan except the two workspace-source
  additions in Task 16.
