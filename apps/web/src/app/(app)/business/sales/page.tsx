import { SalesInsights } from "@/features/crm/SalesInsights";
import { crmCaps } from "@/features/crm/crm-caps";
import { SalesPipelineView } from "@/features/sales/SalesPipelineView";

/** `/business/sales` — pipeline overview + funnel / forecast / ranking (R-DEC-93, R-DEC-175). */
export default async function SalesPipelinePage() {
  const c = await crmCaps();
  return (
    <div className="flex flex-col gap-6">
      <SalesPipelineView />
      <div className="mx-auto w-full max-w-[1400px]"><SalesInsights canSeeDeals={c.canSeeDeals} userId={c.userId} /></div>
    </div>
  );
}
