/**
 * Reports Page Redirect
 * Redirects /reports to /dashboard/reports
 */

import { redirect } from "next/navigation";

export default function ReportsPage() {
  redirect("/dashboard/reports");
}
