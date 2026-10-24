import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { AiControlCenter } from "@/features/admin/ai/AiControlCenter";

/** SCR-64 `/admin/ai` (T-644F/T-646F) — ADM/CEO with `ai:admin` (guard in middleware, R-DEC-79). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  const u = session?.user;
  return <AiControlCenter viewer={{ id: u?.id ?? "", role: u?.role ?? "", permissions: u?.permissions ?? [] }} />;
}
