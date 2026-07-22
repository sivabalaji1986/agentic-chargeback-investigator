import { useState } from "react";
import type { DecisionCardData } from "../types";
import { ACTIONS_URL } from "../lib/agent";

interface DecisionCardProps {
  data: DecisionCardData | null;
  investigatorId: string;
}

export function DecisionCard({ data, investigatorId }: DecisionCardProps) {
  const [submittedAction, setSubmittedAction] = useState<string | null>(null);

  if (!data) {
    return <p className="text-slate-500">Awaiting decision card...</p>;
  }

  async function submit(action: string): Promise<void> {
    await fetch(ACTIONS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision_id: `DEC-${Date.now()}`,
        investigation_id: data!.investigationId,
        case_id: data!.investigationId,
        investigator_id: investigatorId,
        selected_action: action,
        recommendation_shown: data!.recommendation,
        decided_at: new Date().toISOString(),
      }),
    });
    setSubmittedAction(action);
  }

  return (
    <div className="rounded border border-slate-800 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">Decision</p>
      <p className="mt-1 text-slate-100">{data.explanation}</p>
      <div className="mt-3 flex gap-2">
        {data.allowedActions.map((action) => (
          <button
            key={action}
            type="button"
            disabled={submittedAction !== null}
            onClick={() => {
              void submit(action);
            }}
            className="rounded bg-slate-800 px-3 py-1 text-sm text-slate-100 disabled:opacity-40"
          >
            {action.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      {submittedAction && (
        <p className="mt-2 text-sm text-emerald-400">Recorded: {submittedAction.replaceAll("_", " ")}</p>
      )}
    </div>
  );
}
