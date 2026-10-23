/** Client helper (T-610c, R-DEC-28): ask `api/demo-credentials` for a demo password. */
export async function fetchDemoPassword(email: string): Promise<string | null> {
  try {
    const res = await fetch("/api/demo-credentials", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const json = (await res.json()) as { data?: { password?: unknown } };
    return typeof json.data?.password === "string" && json.data.password ? json.data.password : null;
  } catch {
    return null;
  }
}
