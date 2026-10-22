import { getTranslations } from "next-intl/server";

/** SCR-xx approval inbox — placeholder target for the role-aware nav (S5a). */
export default async function ApprovalsPage() {
  const t = await getTranslations("nav");
  return (
    <div className="mx-auto max-w-3xl" data-testid="approvals">
      <h1 className="text-2xl font-semibold">{t("approvals")}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t("approvalsPending")}</p>
    </div>
  );
}
