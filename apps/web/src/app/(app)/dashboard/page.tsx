import { DashboardView } from "@/features/dashboard/DashboardView";

/**
 * SCR-01..04 Dashboard (CEO, CFO, Sales Director, HR Manager) per 06 §4.1..4.4 & T-111.
 * Dynamically adapts pillars, metrics, and alerts to the authenticated user's role.
 */
export default function DashboardPage() {
  return <DashboardView />;
}
