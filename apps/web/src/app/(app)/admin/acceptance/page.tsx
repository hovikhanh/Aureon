import { AcceptanceView } from "@/features/admin/acceptance/AcceptanceView";

/** SCR-64 `/admin/acceptance` (M3.5) — `dashboard:read`, CEO/DIR (guard `/admin` prefix in middleware). */
export default function Page() {
  return <AcceptanceView />;
}
