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
