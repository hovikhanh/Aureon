/** Local calendar day `YYYY-MM-DD` (risk badges are computed after the client-side fetch, so SSR never renders them). */
export function business_today(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
