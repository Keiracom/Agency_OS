/**
 * FILE: app/dashboard/pipeline/layout.tsx
 * PURPOSE: Scoped light theme wrapper for the pipeline stream page
 * Layer: Frontend layout
 */

export default function PipelineLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-theme="light" className="min-h-screen" style={{ backgroundColor: "var(--bg-void)" }}>
      {children}
    </div>
  );
}
