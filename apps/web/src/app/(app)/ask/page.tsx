import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ChatView } from "@/features/ai/ChatView";

/** SCR `/ask` — chat + ActionCard for `suggested_actions` (T-645F needs the viewer id/permissions).
 * `?q=` (M2.4, from ⌘K) prefills and auto-sends the question once. */
export default async function AiPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const session = await getServerSession(authOptions);
  const { q } = await searchParams;
  return (
    <ChatView
      viewer={{ id: session?.user.id ?? "", permissions: session?.user.permissions ?? [] }}
      initialQuestion={q}
    />
  );
}
