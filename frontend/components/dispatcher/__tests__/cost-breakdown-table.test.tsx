/**
 * FILE: frontend/components/dispatcher/__tests__/cost-breakdown-table.test.tsx
 * PURPOSE: Render tests for CostBreakdownTable — LAW II AUD compliance + states.
 * KEI: KEI-159 (KEI-114B)
 */

import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { CostBreakdownTable } from "../cost-breakdown-table";
import type { CostRow } from "../cost-breakdown-table";

const sampleRows: CostRow[] = [
  { taskId: "t-1", title: "Enrichment run", costAud: 0.05, completedAt: "2026-05-01T10:00:00Z" },
  { taskId: "t-2", title: "Outreach batch", costAud: 1.23, completedAt: "2026-05-02T12:00:00Z" },
  { taskId: "t-3", title: "CIS scoring",    costAud: 0.18, completedAt: "2026-05-03T08:00:00Z" },
];

describe("CostBreakdownTable", () => {
  it("renders loading skeleton when loading=true", () => {
    render(<CostBreakdownTable rows={[]} loading={true} />);
    expect(screen.getByRole("status", { name: /loading cost breakdown/i })).toBeDefined();
  });

  it("renders empty-state message when rows is empty", () => {
    render(<CostBreakdownTable rows={[]} />);
    expect(screen.getByText(/no cost data available/i)).toBeDefined();
  });

  it("renders rows sorted by costAud descending by default", () => {
    render(<CostBreakdownTable rows={sampleRows} />);
    const cells = screen.getAllByRole("cell").filter((c) =>
      /A\$\d/.test(c.textContent ?? "")
    );
    const values = cells.map((c) => parseFloat((c.textContent ?? "").replace(/[^0-9.]/g, "")));
    expect(values[0]).toBeGreaterThanOrEqual(values[1]);
    expect(values[1]).toBeGreaterThanOrEqual(values[2]);
  });

  it("renders em-dash for null costAud", () => {
    const rows: CostRow[] = [
      { taskId: "t-null", title: "No cost", costAud: null, completedAt: null },
    ];
    render(<CostBreakdownTable rows={rows} />);
    // Both cost and completedAt are null → two em-dashes rendered
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("renders AUD suffix in every cost cell for populated rows", () => {
    render(<CostBreakdownTable rows={sampleRows} />);
    const audCells = screen.getAllByRole("cell").filter((c) =>
      /AUD/.test(c.textContent ?? "")
    );
    expect(audCells.length).toBeGreaterThanOrEqual(sampleRows.length);
  });

  it("renders task title and task ID for each row", () => {
    render(<CostBreakdownTable rows={sampleRows} />);
    for (const row of sampleRows) {
      expect(screen.getByText(row.title)).toBeDefined();
      expect(screen.getByText(row.taskId)).toBeDefined();
    }
  });
});
