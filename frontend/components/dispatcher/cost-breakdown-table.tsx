/**
 * FILE: frontend/components/dispatcher/cost-breakdown-table.tsx
 * PURPOSE: Per-task cost table, sortable by cost descending (default).
 * KEI: KEI-159 (KEI-114B) — Cost Display implementation.
 * LAW II: All cost values show explicit AUD suffix.
 * Sonar S6759: Props wrapped in Readonly<T>.
 */

export type CostRow = {
  taskId: string;
  title: string;
  costAud: number | null;
  completedAt: string | null;
};

type CostBreakdownTableProps = {
  rows: CostRow[];
  loading?: boolean;
};

function LoadingSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading cost breakdown"
      className="animate-pulse space-y-2"
    >
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-10 w-full rounded bg-muted" />
      ))}
    </div>
  );
}

function formatCostAud(costAud: number | null): string {
  if (costAud === null) return "—";
  return `A$${costAud.toFixed(4)} AUD`;
}

function formatDate(completedAt: string | null): string {
  if (!completedAt) return "—";
  return new Date(completedAt).toLocaleDateString("en-AU", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function CostBreakdownTable({ rows, loading = false }: Readonly<CostBreakdownTableProps>) {
  if (loading) {
    return <LoadingSkeleton />;
  }

  const sorted = [...rows].sort((a, b) => {
    const av = a.costAud ?? -Infinity;
    const bv = b.costAud ?? -Infinity;
    return bv - av;
  });

  return (
    <div className="rounded-xl border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="px-4 py-3 font-medium">Task ID</th>
            <th className="px-4 py-3 font-medium">Title</th>
            <th className="px-4 py-3 font-medium">Cost (AUD)</th>
            <th className="px-4 py-3 font-medium">Completed</th>
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={4} className="px-4 py-6 text-center text-muted-foreground">
                No cost data available yet.
              </td>
            </tr>
          ) : (
            sorted.map((row) => (
              <tr key={row.taskId} className="border-b last:border-0">
                <td className="px-4 py-3 font-mono text-xs">{row.taskId}</td>
                <td className="px-4 py-3">{row.title}</td>
                <td className="px-4 py-3">{formatCostAud(row.costAud)}</td>
                <td className="px-4 py-3 text-muted-foreground">{formatDate(row.completedAt)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
