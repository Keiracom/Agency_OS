/**
 * Layout Components - Main dashboard layout building blocks
 *
 * These components provide the structural foundation for the Agency OS dashboard:
 * - DashboardShell: Main wrapper with sidebar and header
 * - Sidebar: Navy navigation sidebar
 * - Header: White header bar with search and user info
 *
 * Usage:
 * ```tsx
 * import { DashboardShell, Sidebar, Header } from './layout';
 *
 * // Full dashboard layout
 * <DashboardShell title="Dashboard" activePath="/dashboard">
 *   <YourContent />
 * </DashboardShell>
 *
 * // Or use individual components
 * <Sidebar activePath="/campaigns" onNavigate={handleNav} />
 * <Header title="Campaigns" userName="Acme Agency" />
 * ```
 */

export { DashboardShell } from "./DashboardShell";
export type { DashboardShellProps } from "./DashboardShell";

export { Sidebar } from "./Sidebar";
export type { SidebarProps } from "./Sidebar";

export { Header } from "./Header";
export type { HeaderProps } from "./Header";
