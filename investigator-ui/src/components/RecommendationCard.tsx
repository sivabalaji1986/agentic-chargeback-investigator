interface RecommendationCardProps {
  recommendation: string | null;
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  if (!recommendation) {
    return <p className="text-slate-500">Awaiting recommendation...</p>;
  }
  return (
    <div className="rounded border border-slate-800 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">Recommendation</p>
      <p className="text-lg font-semibold text-slate-100">{recommendation.replaceAll("_", " ")}</p>
    </div>
  );
}
