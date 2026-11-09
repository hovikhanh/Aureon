import { RecordsTabs } from "@/features/records/RecordsTabs";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/product/records` (D-21) — record management of the frozen product module (R-DEC-16: no sidebar item). */
export default async function Page() {
  return <RecordsTabs domain="product" caps={await recordCaps("product")} />;
}
