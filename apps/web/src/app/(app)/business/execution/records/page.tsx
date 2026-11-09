import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/execution/records` (D-21) — create / edit / delete meetings, decisions and projects. */
export default async function Page() {
  return <RecordsTabs domain="execution" caps={await recordCaps("execution")} />;
}
