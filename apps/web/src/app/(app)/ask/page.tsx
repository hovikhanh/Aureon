import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ChatView } from "@/features/ai/ChatView";

/** SCR `/ask` — chat + ActionCard for `suggested_actions` (T-645F needs the viewer id/permissions). */
export default async function AiPage() {
  const session = await getServerSession(authOptions);
  return <ChatView viewer={{ id: session?.user.id ?? "", permissions: session?.user.permissions ?? [] }} />;
}
