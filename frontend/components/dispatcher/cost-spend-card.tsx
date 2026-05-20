/**
 * FILE: frontend/components/dispatcher/cost-spend-card.tsx
 * PURPOSE: Cumulative AUD spend card for the dispatcher costs dashboard.
 * KEI: KEI-159 (KEI-114B) — Cost Display implementation.
 * LAW II: All monetary values displayed with explicit AUD suffix.
 * Sonar S6759: Props wrapped in Readonly<T>.
 */

type CostSpendCardProps = {
  totalAud: number | null;
  periodLabel: string;
  loading?: boolean;
};

function LoadingSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading spend data"
      className="animate-pulse rounded-xl border bg-card p-6"
    >
      <div className="h-4 w-32 rounded bg-muted" />
      <div className="mt-4 h-8 w-48 rounded bg-muted" />
      <div className="mt-2 h-3 w-24 rounded bg-muted" />
    </div>
  );
}

export function CostSpendCard({ totalAud, periodLabel, loading = false }: Readonly<CostSpendCardProps>) {
  if (loading) {
    return <LoadingSkeleton />;
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <p className="text-sm font-medium text-muted-foreground">Total Spend</p>
      {totalAud === null ? (
        <p className="mt-2 text-2xl font-semibold text-foreground">No spend yet</p>
      ) : (
        <p className="mt-2 text-2xl font-semibold text-foreground">
          {`A$${totalAud.toFixed(2)} AUD`}
        </p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">{periodLabel}</p>
    </div>
  );
}
