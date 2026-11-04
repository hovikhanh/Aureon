import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/hr/records` (M7) — create / edit / archive the hr records over the existing API. */
export default async function Page() {
  return <RecordsTabs domain="hr" caps={await recordCaps("hr")} />;
}
