import type { TimelineMilestone } from "../types";

const MILESTONE_ORDER: { key: string; label: string }[] = [
  { key: "investigation.accepted", label: "Investigation Started" },
  { key: "specialist.started", label: "MCP Lookup" },
  { key: "specialist.finding_received", label: "Transaction Loaded" },
  { key: "recommendation.produced", label: "Recommendation Ready" },
  { key: "investigation.completed", label: "Investigation Completed" },
];

interface InvestigationTimelineProps {
  seenEventNames: Set<string>;
}

export function InvestigationTimeline({ seenEventNames }: InvestigationTimelineProps) {
  const milestones: TimelineMilestone[] = MILESTONE_ORDER.map(({ key, label }) => ({
    key,
    label,
    status: seenEventNames.has(key) ? "done" : "pending",
  }));

  return (
    <ol className="flex flex-col gap-2">
      {milestones.map((milestone) => (
        <li key={milestone.key} className="flex items-center gap-2">
          <span
            className={
              milestone.status === "done"
                ? "h-2 w-2 rounded-full bg-emerald-400"
                : "h-2 w-2 rounded-full bg-slate-600"
            }
          />
          <span className={milestone.status === "done" ? "text-slate-100" : "text-slate-500"}>
            {milestone.label}
          </span>
        </li>
      ))}
    </ol>
  );
}
