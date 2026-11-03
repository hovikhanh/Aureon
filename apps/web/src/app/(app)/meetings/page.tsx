import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { MeetingsTabs } from "@/features/execution/MeetingsTabs";
import { MeetingsView } from "@/features/execution/MeetingsView";

/** SCR-44 `/meetings` (M2.3): C2 natural-language / short voice note → predicted action items. */
export default async function MeetingsPage() {
  const session = await getServerSession(authOptions);
  return (
    <div className="flex flex-col gap-4">
      <MeetingsTabs active="meetings" />
      <MeetingsView viewerId={session?.user.id ?? ""} permissions={session?.user.permissions ?? []} />
    </div>
  );
}
