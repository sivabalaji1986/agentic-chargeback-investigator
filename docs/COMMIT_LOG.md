# Commit Log

## 2026-07-22 — Add Dispute MCP Server section to README

**Files:** `README.md`
**What:** Added a section describing the 4 tool groups (13 tools total), the write-tool contract reuse, and how to run/test the server locally.
**Why:** Document the Prompt 3 deliverable so the README stays an accurate map of the repository.

## 2026-07-22 — Add mcp-test and mcp-run Makefile targets

**Files:** `Makefile`
**What:** Added `make mcp-test` (runs the dispute-mcp-server test suite) and `make mcp-run` (runs the server locally).
**Why:** Match the developer-command conventions already established for the rest of the workspace.

## 2026-07-22 — Add runnable dispute-mcp-server Docker Compose service

**Files:** `docker-compose.yml`, `dispute-mcp-server/Dockerfile`
**What:** Replaced the comments-only Prompt-1 scaffold with a real, single-service Compose definition (no port mapping — the server communicates over MCP's stdio transport, not HTTP) and a `uv`-based Dockerfile. Verified with a real `docker compose build`, which succeeded in this environment (image `agentic-chargeback-investigator/dispute-mcp-server:local`, confirmed via `docker images`), plus an in-container import smoke test.
**Why:** Prompt 3 explicitly required a runnable service, not just valid-looking YAML; this environment had a working Docker daemon, so the build was actually exercised rather than only statically validated.

## 2026-07-22 — Remove dispute-mcp-server Prompt-1 smoke test; strict-check it in mypy

**Files:** `pyproject.toml`, `dispute-mcp-server/tests/test_import.py` (deleted), 4 dispute-mcp-server files reformatted
**What:** Deleted the superseded import-smoke test and removed `dispute-mcp-server` from the root mypy `[tool.mypy] exclude` list (9 → 8 packages), so the whole package is now strict-mypy-checked like `contracts`. Bundled a mechanical `ruff format` fix for 4 files that had accumulated whitespace/line-wrap drift across earlier tasks (verified whitespace-only, no logic change).
**Why:** This package now has 38 real tests (Tasks 3-10) — the Prompt-1-era exclusion and smoke test are no longer needed.

## 2026-07-22 — Wire main.py entrypoint and add server startup/discovery tests

**Files:** `dispute-mcp-server/src/dispute_mcp_server/main.py`, `dispute-mcp-server/tests/test_server_startup.py`
**What:** `create_app()` builds the `FastMCP` instance, a fresh `DisputeRepository`, and registers all 4 tool groups; a module-level `mcp = create_app()` is exposed for Docker/Makefile use. Tests confirm all 13 tools are discoverable via `Client.list_tools()` and that creating the app twice doesn't error (no shared state between instances).
**Why:** This is the point where all 13 previously-unwired tools become one working server.

## 2026-07-22 — Add merchant tool group

**Files:** `dispute-mcp-server/src/dispute_mcp_server/tools/merchant_tools.py`, `dispute-mcp-server/tests/test_merchant_tools.py`
**What:** Added `get_merchant_evidence`, `get_delivery_details`, `get_cancellation_details` — all three propagate `NotFoundError` for an unknown case_id.
**Why:** Completes the 4th and final MCP tool group.

## 2026-07-22 — Add customer tool group

**Files:** `dispute-mcp-server/src/dispute_mcp_server/tools/customer_tools.py`, `dispute-mcp-server/tests/test_customer_tools.py`
**What:** Added `get_customer_profile`, `get_prior_disputes`, `get_refund_history`. The latter two correctly distinguish an unknown customer_id (raises) from a known customer with no history (returns an empty tuple) — verified against seed data (`CUST-3002` has no prior disputes or refund history).
**Why:** Exposes customer-history data for the future customer-history specialist agent.

## 2026-07-22 — Add transaction tool group

**Files:** `dispute-mcp-server/src/dispute_mcp_server/tools/transaction_tools.py`, `dispute-mcp-server/tests/test_transaction_tools.py`
**What:** Added `get_transaction`, `get_authorization`, `get_settlement`, `get_refund_or_reversal` — all read-only, all propagate `NotFoundError` for an unknown transaction_id.
**Why:** Exposes transaction-domain data for the future transaction specialist agent.

## 2026-07-22 — Add case tool group (get_case, update_case, write_audit)

**Files:** `dispute-mcp-server/src/dispute_mcp_server/tools/__init__.py`, `dispute-mcp-server/src/dispute_mcp_server/tools/case_tools.py`, `dispute-mcp-server/tests/test_case_tools.py`
**What:** Added the first FastMCP tool group. `get_case` propagates `NotFoundError`; `update_case`/`write_audit` reuse `chargeback_contracts.mcp`'s write-side contracts and catch `NotFoundError` internally, returning a structured `McpWriteResponse(status=FAILURE, ...)` instead of raising. Established (and empirically confirmed against the real `fastmcp==3.4.4` package) that `Client.call_tool(...).data` for a Pydantic-model-typed tool return requires **attribute access**, not dict-subscript — a finding carried into every later tool-group task's tests.
**Why:** Proves the case-management boundary end-to-end and de-risks the calling convention for every remaining tool group.

## 2026-07-22 — Add config and structured tool-call logging

**Files:** `dispute-mcp-server/src/dispute_mcp_server/config.py`, `dispute-mcp-server/src/dispute_mcp_server/logging.py`, `dispute-mcp-server/tests/test_logging.py`
**What:** Added environment-backed `Settings`/`load_settings()` and a `log_tool_call` decorator that logs tool name, one relevant identifier, success/failure, and duration — verified to log only the failing exception's type name, never its message text or the full record contents.
**Why:** Satisfies the "avoid logging sensitive payloads" requirement while still giving every tool call an audit trail.

## 2026-07-22 — Add repository layer with seed-data consistency tests

**Files:** `dispute-mcp-server/src/dispute_mcp_server/repository.py`, `dispute-mcp-server/tests/test_seed_data_consistency.py`
**What:** Added `DisputeRepository` (typed lookups over the seeded data, plus the two narrow mutations `update_case_status`/`append_audit_record`) and `NotFoundError`. The repository copies `seed_data.CASES` into its own instance dict rather than aliasing it, so mutations never leak into shared module state or other instances. 8 tests verify every cross-reference in the seed data.
**Why:** This is the boundary between "static seed data" and "queryable service data" — getting the copy-vs-alias and unknown-vs-empty distinctions right here matters for every tool built on top of it.

## 2026-07-22 — Add deterministic cross-referenced seed data

**Files:** `dispute-mcp-server/src/dispute_mcp_server/seed_data.py`
**What:** Added 3 fully cross-referenced mock cases (`CASE-1001`/`1002`/`1003`, covering `goods_not_received`/`duplicate_transaction`/`cancelled_service`) spanning transactions, authorizations, settlements, refunds, customer profiles, prior disputes, refund history, merchant evidence, delivery details, and cancellation details — all internally consistent (amounts/currencies match across case→transaction→authorization→settlement).
**Why:** Every MCP tool needs real, referenceable data to return; future prompts can rely on these same IDs.

## 2026-07-22 — Teach ruff's isort that workspace packages are first-party

**Files:** `pyproject.toml`, 12 already-existing test files across `contracts/` and `dispute-mcp-server/`
**What:** Added `[tool.ruff.lint.isort] known-first-party` listing every workspace package. Without it, ruff's I001 rule treated in-repo packages like `chargeback_contracts` as third-party, merging their imports alphabetically with real third-party packages instead of sorting them into their own group — first noticed when Task 2's `models.py` had to reorder its imports to satisfy ruff.
**Why:** Fixes recurring import-ordering friction proactively before every remaining task in this batch (all of which import `chargeback_contracts`) would otherwise hit the same issue independently.

## 2026-07-22 — Add local response models for dispute-mcp-server read tools

**Files:** `dispute-mcp-server/src/dispute_mcp_server/models.py`
**What:** Added 12 Pydantic models (`CaseRecord`, `TransactionRecord`, `AuthorizationRecord`, `SettlementRecord`, `RefundOrReversalRecord`, `CustomerProfileRecord`, `PriorDisputeRecord`, `RefundHistoryEntry`, `MerchantEvidenceRecord`, `DeliveryDetailsRecord`, `CancellationDetailsRecord`, `AuditRecord`), reusing `chargeback_contracts.skills.DisputeType` rather than redefining it.
**Why:** Prompt 2's `chargeback_contracts.mcp` read-side contracts were deliberately minimal pending a real business schema — this prompt is where that schema now needs to exist, package-local rather than added to the shared contract layer.

## 2026-07-22 — Add dispute-mcp-server dependencies (fastmcp, contracts)

**Files:** `dispute-mcp-server/pyproject.toml`, `uv.lock`
**What:** Added `fastmcp==3.4.4`, `pydantic>=2.13`, and a workspace-local dependency on `contracts`.
**Why:** These are the exact versions this prompt's FastMCP server is built against.

## 2026-07-22 — Add dispute-mcp-server implementation plan

**Files:** `docs/superpowers/plans/2026-07-22-dispute-mcp-server.md`
**What:** Task-by-task plan (16 tasks) to implement Prompt 3's FastMCP server via subagent-driven-development.
**Why:** Break the server build into reviewable, independently-testable units before implementation began.

## 2026-07-22 — Refine dispute-mcp-server contract-reuse decision

**Files:** `docs/superpowers/specs/2026-07-22-dispute-mcp-server-design.md`
**What:** Decided to reuse `chargeback_contracts.mcp`'s write-side envelope contracts as-is for `update_case`/`write_audit`, but define new local models for every read tool instead of wrapping richer mock data in Prompt 2's deliberately-minimal `GetCaseResponse`/`GetTransactionResponse` placeholders.
**Why:** Resolve the tension between "reuse existing contracts" and "these specific contracts were deliberately left minimal" before writing the implementation plan.

## 2026-07-22 — Add dispute-mcp-server design spec

**Files:** `docs/superpowers/specs/2026-07-22-dispute-mcp-server-design.md`
**What:** Recorded real `fastmcp==3.4.4` API research (tool registration via `@mcp.tool`, in-memory testing via `fastmcp.Client`, error propagation as `ToolError`) ahead of planning. Also records that an earlier, mistakenly-sent Prompt 3 (Agent Registry) was withdrawn before any repository changes were made for it.
**Why:** Ground the implementation plan in verified SDK behavior rather than assumption, per the prompt's own instruction to inspect real APIs first.

## 2026-07-22 — Add shared contract layer overview to README

**Files:** `README.md`
**What:** Added a "Shared contract layer" section describing the now-complete `contracts` package, its dependency direction (every service depends inward on it, it depends on nothing), and where official A2A/AG-UI types come from vs. what's application-owned.
**Why:** Document the Prompt 2 deliverable so the README stays an accurate map of the repository.

## 2026-07-22 — Wire contracts into orchestrator-agent and transaction-agent

**Files:** `orchestrator-agent/pyproject.toml`, `orchestrator-agent/tests/test_contracts_integration.py`, `transaction-agent/pyproject.toml`, `transaction-agent/tests/test_contracts_integration.py`, `uv.lock`
**What:** Added `contracts` as a workspace-local dependency (via `[tool.uv.sources] contracts = { workspace = true }`) to both packages, plus one integration test each proving `chargeback_contracts` is consumable from the package root — no business logic added.
**Why:** Satisfy the requirement that the contract layer be proven usable from at least two dependent packages, not just self-tested in isolation.

## 2026-07-22 — Narrow the mypy tests/ exclusion and strict-check contracts

**Files:** `pyproject.toml`, 8 `contracts/src/chargeback_contracts/*.py` modules, 4 `contracts/tests/*.py` files
**What:** Replaced Prompt 1's blanket `exclude = ["(^|/)tests/"]` with an explicit list of the 9 packages that still only have trivial import-smoke tests, so `contracts/tests/` is strict-mypy-checked for the first time. Fixed every `field_validator`'s `info: object` parameter to the correct `pydantic.ValidationInfo` type (removing the now-unneeded `# type: ignore` hedges) across 8 modules, added a `TypedDict` for a test fixture, and added 3 narrow `# type: ignore[call-arg]` on tests that intentionally pass an unexpected keyword to prove `extra="forbid"` rejection at runtime.
**Why:** Prompt 2 introduced real test logic in `contracts/`, so the temporary technical debt from Prompt 1 (documented at the time as removable "once a later prompt adds real tests") could finally be paid down for this package, without touching the other 9 packages, which remain out of scope.

## 2026-07-22 — Expose the contracts public surface from the package root

**Files:** `contracts/src/chargeback_contracts/__init__.py`, `contracts/tests/test_public_surface.py`
**What:** Re-exported all 12 modules' public types/constants/functions (70 names) from `chargeback_contracts`, and added tests proving every exported name resolves, no official A2A protocol model names (`AgentCard`/`AgentSkill`/`Task`/`Message`/`Artifact`/`Part`/`TaskState`) are duplicated locally, and the full 12-module dependency graph has no circular imports.
**Why:** Give consuming packages one clean import surface instead of requiring them to know the internal module layout.

## 2026-07-22 — Add investigation record contract with mandatory-approval validation

**Files:** `contracts/src/chargeback_contracts/records.py`, `contracts/tests/test_records.py`
**What:** Added `InvestigationRecord` (the DAG's root — request, discovered skills, missing-capability warnings, specialist findings, policy interpretation, recommendation, explanation, investigator decision, timestamps, workflow status, audit correlation ID) and `WorkflowStatus`. A `COMPLETED` record cannot validate without an `InvestigatorDecision`; `PARTIAL`/`FAILED` records correctly can. Also added a non-blank validator for `audit_correlation_id`, matching every sibling identifier field elsewhere in the contract layer (a gap in the original plan's sample code, caught during review).
**Why:** This is the structural enforcement of "human approval is mandatory" for the whole system — a completed investigation literally cannot be represented without a recorded human decision.

## 2026-07-22 — Add MCP boundary request/response contracts

**Files:** `contracts/src/chargeback_contracts/mcp.py`, `contracts/tests/test_mcp.py`
**What:** Added read-side (`get_case`, `get_transaction`, `get_customer_history`, `get_merchant_evidence`, `list_case_documents`) and write-side (`create_evidence_request_task`, `update_case_status`, `create_audit_entry`) request/response contracts. Every write request requires a non-blank idempotency key. `get_customer_history` reuses `CustomerHistoryFindingDetails`; `get_merchant_evidence`/`list_case_documents` reuse `EvidenceRef` — `get_case`/`get_transaction` stay deliberately minimal since no case/transaction business schema exists yet in this prompt's scope.
**Why:** Define the MCP-facing boundary shape without implementing MCP tools or inventing a mock business schema ahead of the prompt that will actually build `dispute-mcp-server`.

## 2026-07-22 — Resolve ruff lint findings across contracts

**Files:** 7 `contracts/src/chargeback_contracts/*.py` modules, 10 `contracts/tests/*.py` files
**What:** Migrated every `str`+`Enum` contract enum to `enum.StrEnum` (ruff's `UP042`, matching the Python-3.13-target modernization rule already selected in the root config), sorted import blocks, preferred `datetime.UTC` over `timezone.utc`, and wrapped two lines that exceeded the 100-column limit.
**Why:** Findings had quietly accumulated across the first 11 module tasks; paid down in one pass rather than letting it reach Task 18's final verification as a surprise.

## 2026-07-22 — Add investigator decision contract

**Files:** `contracts/src/chargeback_contracts/decisions.py`, `contracts/tests/test_decisions.py`
**What:** Added `InvestigatorDecision` (decision ID, investigation/case IDs, investigator ID, selected action, optional comments, recommendation shown, decision timestamp, optional A2A IDs) — `investigator_id` and `decided_at` are both required, never optional.
**Why:** No write-side MCP command may be represented as approved without an `InvestigatorDecision` — this is what makes mandatory human approval explicit rather than a convention.

## 2026-07-22 — Add A2UI decision-interface contracts (version 0.9)

**Files:** `contracts/src/chargeback_contracts/a2ui.py`, `contracts/tests/test_a2ui.py`
**What:** Added `InvestigatorAction` (approve/reject/request-more-evidence — human decisions only), 7 discriminated decision-interface component models (decision card, evidence checklist, specialist findings summary, missing-capability warning panel, recommended next actions, approval preview, final decision confirmation), and `A2uiEnvelope` with `version: Literal["0.9"]`.
**Why:** No official A2UI SDK exists; every payload the investigator decision surface will need is defined here, targeting spec version 0.9 exactly.

## 2026-07-22 — Add AG-UI application event payload contracts

**Files:** `contracts/src/chargeback_contracts/agui.py`, `contracts/tests/test_agui.py`
**What:** Added 14 typed event payloads (investigation accepted; capability discovery started/completed; specialist started/progress/finding-received; missing evidence/capability identified; policy interpretation received; recommendation/explanation produced; approval required; investigation completed/failed), each with a stable `event_name` and shared correlation fields. Strengthened the event-name distinctness test to cover all 14 events (it originally checked only 13).
**Why:** These are the typed `value` payloads for `ag_ui.core.CustomEvent`, defined without building the streaming server itself.

## 2026-07-22 — Add missing-capability and deterministic recommendation contracts

**Files:** `contracts/src/chargeback_contracts/recommendation.py`, `contracts/tests/test_recommendation.py`
**What:** Added `MissingCapabilityWarning` (explicit, typed — never a generic exception) and `InvestigationRecommendation` (`RecommendationType` — accept/reject/request-more-evidence — plus deterministic reason codes, supporting finding IDs, missing evidence, warnings, policy references, and an independent `explanation` field). Rewrote the independence test to use real constructor calls in both directions instead of `model_copy` (which bypasses validators and would have passed even if the fields were secretly coupled).
**Why:** This is the architectural core of "recommendation is deterministic, explanation is descriptive and may later be LLM-generated" — the two must never be coupled.

## 2026-07-22 — Add policy interpretation contract

**Files:** `contracts/src/chargeback_contracts/policy.py`, `contracts/tests/test_policy.py`
**What:** Added `PolicyInterpretation` (policy version, cited sections, applicable rules, required/satisfied/missing evidence, exceptions/escalations, interpretation summary, source references, producing agent ID). No recommendation field.
**Why:** The Policy Agent interprets policy but never decides the final recommendation — enforced by the model simply having no such field.

## 2026-07-22 — Add specialist finding contracts with discriminated detail payloads

**Files:** `contracts/src/chargeback_contracts/findings.py`, `contracts/tests/test_findings.py`
**What:** Added `SpecialistFinding` (common envelope: status, summary, evidence used/missing, warnings, timestamps) with a `details` field discriminated over `TransactionFindingDetails`, `CustomerHistoryFindingDetails`, and `MerchantEvidenceFindingDetails`. Cross-field validation: completed status requires a completion timestamp, partial status requires warnings or missing evidence, completion cannot precede start. No recommendation field.
**Why:** Specialists investigate and report facts; they must never return the final Accept/Reject/Request More Evidence recommendation.

## 2026-07-22 — Add dispute intake contracts (InvestigationRequest, SourceChannel)

**Files:** `contracts/src/chargeback_contracts/dispute.py`, `contracts/tests/test_dispute.py`
**What:** Added `InvestigationRequest` (IDs, source channel, customer narrative, dispute type, amount/currency, submitted timestamp, evidence references, requested skills, optional A2A context ID) and `SourceChannel` (email/contact_centre/web_form/chatbot).
**Why:** The intake payload that starts every investigation, with monetary/timestamp/currency validation reused from `common.py`.

## 2026-07-22 — Add evidence reference contracts with URI scheme validation

**Files:** `contracts/src/chargeback_contracts/evidence.py`, `contracts/tests/test_evidence.py`
**What:** Added `EvidenceRef` (never raw file bytes — a secure `evidence://` URI pointer only) and `EvidenceType` (12 categories). The URI validator rejects any scheme other than `evidence://`, including bare local paths and `file://`; a follow-up fix rejects `..` path-traversal segments within an otherwise-valid `evidence://` URI, closing a gap a future evidence-store resolver could otherwise be tricked by.
**Why:** Evidence references must never expose a local filesystem path or allow reading outside an intended directory.

## 2026-07-22 — Add skill IDs, dispute types, and dispute-to-skill mapping

**Files:** `contracts/src/chargeback_contracts/skills.py`, `contracts/tests/test_skills.py`
**What:** Added `SkillId` (5 stable skill identifiers), `DisputeType` (6 dispute classifications), and `required_skills_for()`, which returns the deterministic skills a dispute type needs, always appending the Policy skill last (it runs only after the evidence specialists report).
**Why:** Declares the specialist-ordering dependency without executing any orchestration.

## 2026-07-22 — Add contracts common primitives (ContractModel, validators)

**Files:** `contracts/src/chargeback_contracts/common.py`, `contracts/tests/test_common.py`
**What:** Added `ContractModel` (the shared Pydantic v2 base, `extra="forbid"`) and reusable validators (`require_non_blank`, `require_utc`, `require_currency_code`, `require_positive_amount`, `require_percentage`) used by every other contract module. Strengthened the UTC-normalization test to actually exercise a non-UTC offset being converted, rather than only round-tripping an already-UTC value.
**Why:** The DAG's leaf module — every later module builds on these primitives rather than reimplementing validation logic.

## 2026-07-22 — Add contracts package runtime dependencies

**Files:** `contracts/pyproject.toml`, `uv.lock`
**What:** Added `pydantic>=2.13`, `a2a-sdk==1.1.1`, and `ag-ui-protocol==0.1.19` to the `contracts` package (the only package to gain these dependencies in this prompt).
**Why:** These are the exact versions the contract layer is built against, confirmed to exist on the live registry before use.

## 2026-07-22 — Add shared contract layer implementation plan

**Files:** `docs/superpowers/plans/2026-07-21-shared-contract-layer.md`
**What:** Task-by-task plan (19 tasks) to implement Prompt 2's contract layer via subagent-driven-development.
**Why:** Break the large contract-layer build into reviewable, independently-testable units before implementation began.

## 2026-07-22 — Refine shared contract layer design (drop registry.py, scope mcp.py)

**Files:** `docs/superpowers/specs/2026-07-21-shared-contract-layer-design.md`
**What:** Merged `MissingCapabilityWarning` into `recommendation.py` instead of shipping an otherwise-empty `registry.py` (no prompt section mapped to it), and documented the MCP read-result scoping decision (reuse existing finding/evidence shapes where they fit; stay minimal where no business schema exists yet).
**Why:** Lock in file-split refinements discovered while fleshing out the plan, before writing any code.

## 2026-07-22 — Add shared contract layer design spec

**Files:** `docs/superpowers/specs/2026-07-21-shared-contract-layer-design.md`
**What:** Recorded real `a2a-sdk` 1.1.1 / `ag-ui-protocol` 0.1.19 API research (both inspected directly rather than guessed) and the execution decisions confirmed with the user ahead of implementation: A2A identifiers carried as validated ID-reference-only fields (never wrapping the SDK's protobuf types), a narrowed mypy `tests/` exclusion documented as temporary technical debt, and a two-package `contracts` dependency wiring plan.
**Why:** Prompt 2 explicitly required inspecting the installed SDK shapes rather than guessing; this is where those findings and the resulting design decisions were captured before planning.

## 2026-07-21 — Write full foundation README

**Files:** `README.md`
**What:** Replaced the one-line title with the full foundation README (purpose, tech overview, repository structure, module responsibility table, prerequisites, setup, developer commands, Ollama note, doc link, staged-development statement).
**Why:** Give the repository a real entry point matching the Prompt 1 specification's README requirements.

## 2026-07-21 — Add root Makefile

**Files:** `Makefile`
**What:** Added the root Makefile with `install`, `lock`, `format`, `lint`, `typecheck`, `test`, `verify`, `ui-install`, `ui-build`, and `clean` targets.
**Why:** Provide the developer commands the Prompt 1 specification requires, all runnable from the repo root.

## 2026-07-21 — Fix investigator-ui build and correct changelog process

**Files:** `investigator-ui/postcss.config.js`, `investigator-ui/package.json`, `investigator-ui/package-lock.json`, `.gitignore`, `docs/COMMIT_LOG.md`
**What:** Fixed the first real `npm run build` failure (Tailwind v4 moved its PostCSS integration to `@tailwindcss/postcss`; the app shell still referenced the old v3 plugin name), added `.gitignore` entries for Node build byproducts (`node_modules/`, `*.tsbuildinfo`, generated `vite.config.js`/`.d.ts`), and reverted two premature `docs/COMMIT_LOG.md` entries the implementer had mistakenly added per-commit.
**Why:** `investigator-ui` needs to actually build (Prompt 1 acceptance criterion); the changelog for this batch is written once, consolidated, here — not per commit — so the premature entries were corrected before this final entry.

## 2026-07-21 — Add investigator-ui Vite/TS/Tailwind app shell

**Files:** `investigator-ui/index.html`, `investigator-ui/vite.config.ts`, `investigator-ui/tsconfig.json`, `investigator-ui/tsconfig.node.json`, `investigator-ui/postcss.config.js`, `investigator-ui/tailwind.config.js`, `investigator-ui/src/index.css`, `investigator-ui/src/App.tsx`, `investigator-ui/src/main.tsx`
**What:** Added the Vite + React + TypeScript + Tailwind app shell: an HTML entrypoint, Vite/TS/PostCSS/Tailwind config, and a placeholder `App` component titled "Agentic Chargeback Investigator" noting the investigation UI comes later.
**Why:** Prompt 1 requires a minimal, buildable frontend shell — no AG-UI/A2UI behavior yet.

## 2026-07-21 — Add investigator-ui package manifest and lockfile

**Files:** `investigator-ui/package.json`, `investigator-ui/package-lock.json`
**What:** Added the frontend package manifest with exact pins (`react@19.2.7`, `react-dom@19.2.7`, `vite@8.1.5`, `tailwindcss@4.3.2`, `@ag-ui/client@0.0.57`) and installed dependencies.
**Why:** Establish the frontend toolchain with the exact versions the Prompt 1 specification requires.

## 2026-07-21 — Add docker-compose scaffold

**Files:** `docker-compose.yml`
**What:** Added a comments-only docker-compose scaffold explaining that full service orchestration lands in a later prompt, and that Ollama is intentionally not defined (it runs natively on the Docker host).
**Why:** Document orchestration intent without fabricating an unverifiable live service definition — this sandbox has no reachable Docker daemon to confirm a clean single-container ChromaDB startup.

## 2026-07-21 — Lock workspace and fix pytest/mypy test-module collision

**Files:** `pyproject.toml`, `uv.lock`
**What:** Ran `uv lock`/`uv sync` for the first time and fixed a real pytest/mypy "duplicate module" collision caused by all 10 packages sharing the `tests/test_import.py` basename with no `__init__.py`, via `--import-mode=importlib` (pytest) and a `tests/` exclude (mypy) — no package files touched, `strict = true` left intact.
**Why:** Verify the workspace actually installs and every package imports, per the Prompt 1 acceptance criteria.

## 2026-07-21 — Add knowledge-ingestor package

**Files:** `knowledge-ingestor/pyproject.toml`, `knowledge-ingestor/src/knowledge_ingestor/__init__.py`, `knowledge-ingestor/tests/test_import.py`
**What:** Added the `knowledge-ingestor` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later seed policy knowledge into ChromaDB.

## 2026-07-21 — Add contracts package

**Files:** `contracts/pyproject.toml`, `contracts/src/chargeback_contracts/__init__.py`, `contracts/tests/test_import.py`
**What:** Added the `contracts` workspace member (distribution name `contracts`, import name `chargeback_contracts`).
**Why:** Scaffold the package that will later hold shared Pydantic models and capability constants.

## 2026-07-21 — Add dispute-mcp-server package

**Files:** `dispute-mcp-server/pyproject.toml`, `dispute-mcp-server/src/dispute_mcp_server/__init__.py`, `dispute-mcp-server/tests/test_import.py`
**What:** Added the `dispute-mcp-server` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later expose mock enterprise data through MCP.

## 2026-07-21 — Add agent-registry package

**Files:** `agent-registry/pyproject.toml`, `agent-registry/src/agent_registry/__init__.py`, `agent-registry/tests/test_import.py`
**What:** Added the `agent-registry` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later provide lease-based agent and capability discovery.

## 2026-07-21 — Add duplicate-transaction-agent package

**Files:** `duplicate-transaction-agent/pyproject.toml`, `duplicate-transaction-agent/src/duplicate_transaction_agent/__init__.py`, `duplicate-transaction-agent/tests/test_import.py`
**What:** Added the `duplicate-transaction-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later demonstrate dynamic capability registration.

## 2026-07-21 — Add policy-agent package

**Files:** `policy-agent/pyproject.toml`, `policy-agent/src/policy_agent/__init__.py`, `policy-agent/tests/test_import.py`
**What:** Added the `policy-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later interpret policy using RAG.

## 2026-07-21 — Add merchant-evidence-agent package

**Files:** `merchant-evidence-agent/pyproject.toml`, `merchant-evidence-agent/src/merchant_evidence_agent/__init__.py`, `merchant-evidence-agent/tests/test_import.py`
**What:** Added the `merchant-evidence-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later investigate merchant evidence.

## 2026-07-21 — Add customer-history-agent package

**Files:** `customer-history-agent/pyproject.toml`, `customer-history-agent/src/customer_history_agent/__init__.py`, `customer-history-agent/tests/test_import.py`
**What:** Added the `customer-history-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later investigate customer history.

## 2026-07-21 — Add transaction-agent package

**Files:** `transaction-agent/pyproject.toml`, `transaction-agent/src/transaction_agent/__init__.py`, `transaction-agent/tests/test_import.py`
**What:** Added the `transaction-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later handle transaction-domain investigation.

## 2026-07-21 — Add orchestrator-agent package

**Files:** `orchestrator-agent/pyproject.toml`, `orchestrator-agent/src/orchestrator_agent/__init__.py`, `orchestrator-agent/tests/test_import.py`
**What:** Added the `orchestrator-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later coordinate investigations and deterministic aggregation.

## 2026-07-21 — Add root uv workspace configuration

**Files:** `pyproject.toml`, `.python-version`, `.env.example`
**What:** Added the root `uv` workspace manifest (10-member workspace, shared dev dependencies, Ruff/Mypy/Pytest config), pinned Python to 3.13, and documented environment variable placeholders (Ollama, ChromaDB, registry/MCP URLs, log level).
**Why:** Establish the Prompt 1 foundation's workspace root before any member package exists, per the accompanying design spec.

## 2026-07-21 — Add git-commit skill

**Files:** `.claude/skills/git-commit/SKILL.md`
**What:** Added the git-commit skill, tailored for this Python repo (Python-specific never-stage list, repo name, commit workflow).
**Why:** Give Claude Code a repo-specific, repeatable procedure for committing changes and logging them in docs/COMMIT_LOG.md.

## 2026-07-21 — Add use-case tech summary

**Files:** `docs/use-case-tech-summary.md`
**What:** Added the canonical design reference covering project overview, tech stack, architecture components, specialist agents, responsibility matrix, investigation flow, decision rules, demo scenarios, repository structure, and key architectural principles.
**Why:** Provide a single source of truth for the agentic chargeback investigator design (A2A, MCP, RAG, AG-UI, A2UI) before implementation begins.

## 2026-07-21 — Add project README

**Files:** `README.md`
**What:** Added a README with the project title.
**Why:** Establish a starting point for project documentation.

## 2026-07-21 — Ignore macOS .DS_Store files

**Files:** `.gitignore`
**What:** Added `.DS_Store` to the ignore list.
**Why:** Prevent macOS Finder metadata files from being tracked.
