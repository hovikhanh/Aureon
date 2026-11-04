import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/sales/records` (M7) — create / edit / archive the sales records over the existing API. */
export default async function Page() {
  return <RecordsTabs domain="sales" caps={await recordCaps("sales")} />;
}
