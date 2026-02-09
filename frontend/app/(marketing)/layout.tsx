/**
 * FILE: app/(marketing)/layout.tsx
 * PURPOSE: Marketing pages layout with ISR configuration
 * 
 * ISR Strategy:
 * - Revalidate every 60 seconds (founding spots counter updates)
 * - Static shell, dynamic data refreshes periodically
 */

// Enable ISR for all marketing pages - revalidate every 60 seconds
// This allows founding spots counter to update without full rebuild
export const revalidate = 60;

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
