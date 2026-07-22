import type { StreamEvent } from "../types";

interface EventStreamProps {
  events: StreamEvent[];
}

export function EventStream({ events }: EventStreamProps) {
  return (
    <div className="flex flex-col gap-1 rounded border border-slate-800 p-3 text-sm">
      {events.length === 0 && <p className="text-slate-500">No events yet.</p>}
      {events.map((event, index) => (
        <div key={`${event.name}-${index}`} className="flex justify-between gap-4 text-slate-400">
          <span className="font-mono">{event.name}</span>
          <span>{event.occurredAt}</span>
        </div>
      ))}
    </div>
  );
}
