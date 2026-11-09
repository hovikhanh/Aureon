import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/risk/records` (D-21) — record management of the frozen risk module (R-DEC-16: no sidebar item). */
export default async function Page() {
  return <RecordsTabs domain="risk" caps={await recordCaps("risk")} />;
}
