/**
 * FILE: app/(marketing)/layout.tsx
 * PURPOSE: Marketing pages layout
 * 
 * ISR Strategy:
 * - Each page in this group has its own revalidation config:
 *   - /pricing: 3600s (hourly)
 *   - /about: 3600s (hourly)
 *   - /how-it-works: 3600s (hourly)
 * - Layout itself has no revalidation (passes through to pages)
 * 
 * Note: Page-level revalidation requires Server Components.
 * All pages use the pattern: page.tsx (Server) -> *Client.tsx (Client)
 */

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
