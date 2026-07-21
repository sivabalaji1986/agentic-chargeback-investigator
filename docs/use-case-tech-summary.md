# Use Case Tech Summary

> Canonical design reference for **agentic-chargeback-investigator**.

## 1. Project Overview

### Repository

`agentic-chargeback-investigator`

### Goal

Build an AI-assisted credit card chargeback investigation platform
showcasing **A2A, MCP, RAG, AG-UI, A2UI, dynamic agent registration, and
mandatory human approval**.

### Scope

Customer submits a single chargeback dispute via Email, Contact Centre,
Web Form or Chatbot.

Recommendation: - Accept Chargeback - Reject Chargeback - Request More
Evidence

Final decision is always made by the Investigator.

### Non Goals

-   No card-network/acquirer integration
-   No merchant-system integration
-   No authentication or mTLS
-   No confidence scores
-   No autonomous approval/rejection
-   Single transaction only
-   Mock enterprise systems

------------------------------------------------------------------------

# 2. Technology Stack

  Component      Version
  -------------- -----------------------
  Python         3.13
  uv             Workspace
  FastAPI        0.139.2
  a2a-sdk        1.1.1
  FastMCP        3.4.4
  ChromaDB       1.5.9
  AG-UI Python   ag-ui-protocol 0.1.19
  AG-UI React    @ag-ui/client 0.0.57
  A2UI           v0.9
  React          19.2.7
  Vite           8.1.5
  Tailwind       4.3.2
  Node           22

### Ollama

Runs on the Docker host (not as a container).

Models:

-   `qwen3.5:9b`
-   `nomic-embed-text`

------------------------------------------------------------------------

# 3. Architecture Components

## Orchestrator

Responsibilities:

-   Understand request
-   Classify dispute
-   Discover capabilities
-   Query Agent Registry
-   Coordinate specialists
-   Aggregate findings
-   Apply deterministic recommendation rules
-   Explain recommendation
-   Publish AG-UI events
-   Launch A2UI
-   Write audit through MCP

## Agent Registry

Lease-based runtime capability registry.

## A2A

Communication between Orchestrator and specialist agents.

Supports:

-   Capability routing
-   Parallel execution
-   Structured findings
-   Partial results

## MCP

Single server:

`dispute-mcp-server`

Tool groups:

-   Case
-   Transaction
-   Customer
-   Merchant

Each specialist only accesses its own tool group.

## RAG

ChromaDB stores:

-   Chargeback policies
-   Operational procedures
-   Evidence requirements

Policy Agent retrieves and interprets policy guidance.

## AG-UI

Implemented using the actual AG-UI protocol.

Backend: - ag-ui-protocol 0.1.19

Frontend: - @ag-ui/client 0.0.57

Streams:

-   Progress
-   Findings
-   Missing evidence
-   Missing capability
-   Recommendation
-   Explanation

## A2UI

Investigator decision interface.

Mandatory human approval.

------------------------------------------------------------------------

# 4. Specialist Agents

## Transaction Agent

Capability: `transaction-investigation`

## Customer History Agent

Capability: `customer-history-investigation`

## Merchant Evidence Agent

Capability: `merchant-evidence-investigation`

## Policy Agent

Capability: `chargeback-policy-interpretation`

Runs **after** the three evidence specialists.

Uses RAG to interpret evidence.

Never decides the recommendation.

## Duplicate Transaction Agent

Capability:

`duplicate-transaction-investigation`

Introduced later to demonstrate dynamic capability registration.

------------------------------------------------------------------------

# 5. Responsibility Matrix

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Orchestrator                        Plan, coordinate, aggregate,
                                      deterministic recommendation

  Agent Registry                      Runtime discovery

  Specialists                         Investigation

  Policy Agent                        Policy interpretation

  MCP                                 Enterprise access

  AG-UI                               Streaming

  A2UI                                Human approval

  Investigator                        Final decision
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 6. Investigation Flow

1.  Customer submits dispute.
2.  Orchestrator understands request.
3.  Required capabilities identified.
4.  Agent Registry discovers agents.
5.  Transaction, Customer History and Merchant Evidence Agents execute
    in parallel.
6.  Specialists access `dispute-mcp-server`.
7.  AG-UI streams progress.
8.  Policy Agent executes after the three specialists.
9.  Policy Agent retrieves policy through RAG.
10. Orchestrator aggregates findings.
11. Deterministic rules produce:

-   Accept
-   Reject
-   Request More Evidence

12. LLM explains recommendation.
13. AG-UI streams final outcome.
14. A2UI presents investigator decision.
15. Investigator decides.
16. Case and audit updated through MCP.

------------------------------------------------------------------------

# 7. Decision Rules

-   Recommendation is deterministic.
-   LLM explains but never decides.
-   Human approval is mandatory.
-   Missing evidence ⇒ Request More Evidence.
-   Missing capability ⇒ Partial investigation with explicit warning.

------------------------------------------------------------------------

# 8. Demo Scenarios

## Demo 1

Full investigation using:

-   Transaction Agent
-   Customer History Agent
-   Merchant Evidence Agent
-   Policy Agent

Demonstrates:

-   A2A
-   MCP
-   RAG
-   AG-UI
-   A2UI
-   Deterministic recommendation

## Demo 2

Duplicate transaction capability unavailable.

After deploying `duplicate-transaction-agent`, the same case succeeds
**without changing the Orchestrator**.

------------------------------------------------------------------------

# 9. Repository Structure

``` text
agentic-chargeback-investigator
├── orchestrator-agent
├── transaction-agent
├── customer-history-agent
├── merchant-evidence-agent
├── policy-agent
├── duplicate-transaction-agent
├── agent-registry
├── dispute-mcp-server
├── contracts
├── investigator-ui
├── knowledge-ingestor
├── docker-compose.yml
└── Makefile
```

`knowledge-ingestor` seeds policy knowledge into ChromaDB only.

------------------------------------------------------------------------

# 10. Key Architectural Principles

-   Orchestrator coordinates.
-   Specialists investigate.
-   First three specialists execute in parallel.
-   Policy Agent runs afterwards.
-   Recommendations are deterministic.
-   LLM explains but never decides.
-   Enterprise systems are accessed exclusively through MCP.
-   AG-UI is implemented using the real protocol.
-   A2UI enforces human approval.
-   New capabilities are added without changing the Orchestrator.
-   Ollama runs on the Docker host.
