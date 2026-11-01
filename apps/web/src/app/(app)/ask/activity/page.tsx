import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { AiFeed } from "@/features/ai/AiFeed";

/** SCR `/ask/activity` (M3.2, R-DEC-130) — the "AI đã làm" feed: the viewer's L3 executed actions
 * with a 24h undo. Needs the viewer id/permissions for the reused ActionCard. */
export default async function AiActivityPage() {
  const session = await getServerSession(authOptions);
  return (
    <AiFeed
      viewer={{ id: session?.user.id ?? "", permissions: session?.user.permissions ?? [] }}
    />
  );
}
