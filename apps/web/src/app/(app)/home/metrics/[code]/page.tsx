import { MetricLandingView } from "@/features/dashboard/MetricLandingView";

/**
 * `/home/metrics/[code]` — landing page of an alert notification (R-DEC-88 link, 03 §4). Same
 * EP-12 detail as the P01 dialog on `/home`; scope is enforced by the API (`dashboard:read` +
 * pillar), an out-of-scope metric shows the 403 reason in place. v2.1 `/dashboard/metrics/<code>`
 * bookmarks 308 here through `lib/legacy-routes.ts`.
 */
export default async function Page({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  return <MetricLandingView code={decodeURIComponent(code)} />;
}
