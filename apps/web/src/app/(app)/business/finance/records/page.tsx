import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/finance/records` (M7) — create / edit / archive the finance records over the existing API. */
export default async function Page() {
  return <RecordsTabs domain="finance" caps={await recordCaps("finance")} />;
}
