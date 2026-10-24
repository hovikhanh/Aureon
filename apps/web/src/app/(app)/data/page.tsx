import Link from "next/link";
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { DropZone } from "@/features/capture/DropZone";
import { InboxView } from "@/features/capture/InboxView";

/** SCR-45 `/data` Data Inbox (T-635F). ADM has no inbox (EP-DC-13 → 403): link to SCR-63 + the upload/import zone (R-DEC-76). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  const u = session?.user;
  if (u?.role === "ADM") {
    const t = await getTranslations("capture.inbox");
    return (
      <div className="mx-auto max-w-3xl rounded-lg border bg-card p-6" data-testid="data-inbox-adm" data-scr="SCR-45">
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        <p className="mt-2 text-sm text-muted-foreground">{t("admNotice")}</p>
        <Link href="/admin/data-capture" className="mt-3 inline-block text-primary hover:underline">{t("admLink")}</Link>
        {/* R-DEC-76: ADM imports the org roster (HR_ROSTER, C5) — upload only, no inbox. */}
        {u.permissions.includes("idp:write") && <div className="mt-4"><DropZone /></div>}
      </div>
    );
  }
  return <InboxView permissions={u?.permissions ?? []} role={u?.role ?? ""} />;
}
