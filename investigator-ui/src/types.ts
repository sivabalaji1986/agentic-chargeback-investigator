export interface TimelineMilestone {
  key: string;
  label: string;
  status: "pending" | "done";
}

export interface StreamEvent {
  name: string;
  occurredAt: string;
  raw: Record<string, unknown>;
}

export interface DecisionCardData {
  investigationId: string;
  recommendation: string;
  explanation: string;
  allowedActions: string[];
}
