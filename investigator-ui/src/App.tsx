import { useCallback, useState } from "react";
import { DecisionCard } from "./components/DecisionCard";
import { EventStream } from "./components/EventStream";
import { InvestigationTimeline } from "./components/InvestigationTimeline";
import { RecommendationCard } from "./components/RecommendationCard";
import { createTransactionAgentClient } from "./lib/agent";
import type { DecisionCardData, StreamEvent } from "./types";

interface CustomEventLike {
  type: string;
  name?: string;
  value?: Record<string, unknown>;
}

interface RunFinishedLike {
  result?: {
    investigation_id?: string;
    allowed_actions?: string[];
    components?: Array<Record<string, unknown>>;
  };
}

function App() {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [decisionCard, setDecisionCard] = useState<DecisionCardData | null>(null);
  const [running, setRunning] = useState(false);

  const startInvestigation = useCallback(async () => {
    setEvents([]);
    setRecommendation(null);
    setDecisionCard(null);
    setRunning(true);

    const agent = createTransactionAgentClient();
    await agent.runAgent(
      { forwardedProps: { case_id: "CASE-1001" } },
      {
        onEvent: ({ event }) => {
          const customEvent = event as unknown as CustomEventLike;
          if (customEvent.type === "CUSTOM" && customEvent.name && customEvent.value) {
            setEvents((prev) => [
              ...prev,
              {
                name: customEvent.name!,
                occurredAt: String(customEvent.value!.occurred_at ?? ""),
                raw: customEvent.value!,
              },
            ]);
            if (customEvent.name === "recommendation.produced") {
              setRecommendation(String(customEvent.value.recommendation));
            }
          }
        },
        onRunFinishedEvent: ({ event }) => {
          const result = (event as unknown as RunFinishedLike).result;
          const card = result?.components?.find((c) => c.component_type === "decision_card");
          if (result && card) {
            setDecisionCard({
              investigationId: String(result.investigation_id),
              recommendation: String(card.recommendation),
              explanation: String(card.explanation),
              allowedActions: result.allowed_actions ?? [],
            });
          }
          setRunning(false);
        },
      },
    );
  }, []);

  const seenEventNames = new Set(events.map((event) => event.name));

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-semibold">Agentic Chargeback Investigator</h1>
        <p className="mt-2 text-slate-400">
          Vertical-slice spike: intake harness &rarr; Transaction Agent &rarr; AG-UI &rarr; A2UI.
        </p>
        <button
          type="button"
          onClick={() => {
            void startInvestigation();
          }}
          disabled={running}
          className="mt-4 rounded bg-slate-800 px-4 py-2 text-sm disabled:opacity-40"
        >
          {running ? "Investigating..." : "Start Investigation (CASE-1001)"}
        </button>

        <div className="mt-6 grid gap-6">
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Timeline</h2>
            <InvestigationTimeline seenEventNames={seenEventNames} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Event Stream</h2>
            <EventStream events={events} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Recommendation</h2>
            <RecommendationCard recommendation={recommendation} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Decision</h2>
            <DecisionCard data={decisionCard} investigatorId="inv-demo" />
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
