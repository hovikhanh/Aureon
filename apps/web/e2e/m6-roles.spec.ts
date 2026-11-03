import type { Page, Response } from "@playwright/test";
import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";
import { cleanupReviewDocs, seedReviewDoc } from "./support/seed";

/**
 * TC-M6-04 (e2e) — the five roles of the M6 role QA (CEO, CFO, Kinh doanh, Sales, Reviewer).
 * `@mock` tests also run on the mock BFF; untagged ones need the real API (data, `/org/tree`,
 * `/execution/meetings`, `/calendar/events`). "Kinh doanh" and "Sales" are the same demo account
 * (`sales@abc.demo`, DIR khối C).
 */

/** Every `/api/backend/*` answer ≥ 400 seen while `fn` runs. */
async function backendErrors(page: Page, fn: () => Promise<void>): Promise<string[]> {
  const seen: string[] = [];
  const on = (r: Response) => {
    const u = r.url();
    if (r.status() >= 400 && u.includes("/api/backend/")) seen.push(`${r.status()} ${u.split("/api/backend")[1]}`);
  };
  page.on("response", on);
  try {
    await fn();
  } finally {
    page.off("response", on);
  }
  return seen;
}

test.describe("M6 · CEO", () => {
  test("SEI is one tile like Revenue / Runway; Open Risks opens the alert list → metric detail", { tag: "@mock" }, async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/home");
    const sei = page.getByTestId("exec-sei");
    await expect(sei).toBeVisible();
    await expect(sei.getByTestId("metric-tile")).toHaveCount(1);
    await expect(sei.locator("h2")).toHaveCount(0); // no second card + heading around the tile

    await page.getByTestId("exec-risks-link").click();
    await expect(page).toHaveURL(/\/home\/alerts$/);
    await expect(page.getByTestId("alerts")).toBeVisible();
    const first = page.getByTestId("alert-open").first();
    if (await first.count()) {
      await first.click();
      await expect(page).toHaveURL(/\/home\/metrics\/[^/]+$/);
    }
  });

  test("SEI tile has the same single-Card box as Revenue / Runway; no Card-in-Card in any Home level", { tag: "@mock" }, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/home");
    const sei = page.getByTestId("exec-sei").getByTestId("metric-tile");
    const revenue = page.getByTestId("exec-tiles").getByTestId("metric-tile").first();
    await expect(sei).toBeVisible();
    const box = (l: typeof sei) => l.evaluate((el) => {
      const r = el.getBoundingClientRect(); const c = getComputedStyle(el);
      return { w: Math.round(r.width), h: Math.round(r.height), pad: c.padding, border: `${c.borderTopWidth} ${c.borderTopStyle}`, radius: c.borderTopLeftRadius, shadow: c.boxShadow, bg: c.backgroundColor };
    });
    expect(await box(sei)).toEqual(await box(revenue));
    // a metric tile (itself the Card) must never sit inside another Card (`rounded-lg border bg-card`)
    const nested = () => page.locator("[data-testid=metric-tile]").evaluateAll((els) =>
      els.filter((el) => el.parentElement?.closest(".rounded-lg.border.bg-card")).length);
    expect(await nested()).toBe(0);
    for (const level of ["department", "employee", "executive"] as const) {
      await page.getByTestId(`level-${level}`).click();
      await expect(page.getByTestId({ executive: "exec-view", department: "dept-view", employee: "emp-view" }[level])).toBeVisible();
      expect(await nested(), level).toBe(0);
    }
  });

  test("Khối/Phòng · Dự án trễ hạn opens the projects list filtered to late projects", { tag: "@mock" }, async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/home");
    await page.getByTestId("level-department").click();
    await page.getByTestId("dept-late-link").click();
    await expect(page).toHaveURL(/\/work\/projects\?late=1$/);
    await expect(page.getByTestId("projects-late")).toBeChecked();
  });

  test("Họp & lịch: meetings list + calendar tab load, no hydration error (#418), no 4xx", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (e) => pageErrors.push(e.message));
    await loginSettled(page, "ceo@abc.demo");
    const errs = await backendErrors(page, async () => {
      await page.goto("/meetings");
      await expect(page.getByTestId("meeting-list")).toBeVisible();
      await expect(page.getByTestId("meeting-row").first()).toBeVisible();
      await expect(page.getByTestId("voice-not-available")).toBeVisible(); // R-DEC-166: recording shown as not supported
      await expect(page.getByTestId("voice-start")).toHaveCount(0);
      await page.getByTestId("meetings-tab-calendar").click();
      await expect(page).toHaveURL(/\/meetings\/calendar$/);
      await expect(page.getByTestId("calendar-view")).toBeVisible();
      await page.waitForLoadState("networkidle");
    });
    expect(errs).toEqual([]); // EP-CAL-01 used to answer 422 (datetime sent for a date)
    expect(pageErrors.filter((m) => m.includes("418"))).toEqual([]);
  });
});

test.describe("M6 · CFO (DIR khối F)", () => {
  test("Work screens never call /org/tree (403 outside khối O)", async ({ page }) => {
    await loginSettled(page, "cfo@abc.demo");
    const errs = await backendErrors(page, async () => {
      for (const path of ["/work", "/work?view=board", "/work/projects", "/work/workload", "/goals"]) {
        await page.goto(path);
        await page.waitForLoadState("networkidle");
      }
    });
    expect(errs).toEqual([]);
  });

  test("a khối-F invoice filed by another department opens its review (was 404)", async ({ page }) => {
    // seeded as the reviewer (Hành chính — Trợ lý) → INVOICE, pillar F: listed in the CFO inbox (khối)
    const { document_id } = seedReviewDoc();
    try {
      await loginSettled(page, "cfo@abc.demo");
      await page.goto("/data");
      const row = page.locator(`[data-testid="inbox-row"][data-doc="${document_id}"]`);
      await expect(row).toBeVisible();
      const errs = await backendErrors(page, async () => {
        await row.getByTestId("inbox-review").click();
        await expect(page).toHaveURL(new RegExp(`/data/review/${document_id}$`));
        await expect(page.getByTestId("review-load-error")).toHaveCount(0);
        await page.waitForLoadState("networkidle");
      });
      expect(errs.filter((e) => e.includes("/review") || e.includes("/idp/documents"))).toEqual([]);
    } finally {
      cleanupReviewDocs();
    }
  });
});

test.describe("M6 · Kinh doanh / Sales (DIR khối C)", () => {
  test("HR roster is not offered and its URL shows the 403 page, not a broken screen", { tag: "@mock" }, async ({ page }) => {
    await loginSettled(page, "sales@abc.demo");
    await page.goto("/business");
    await expect(page.getByTestId("business-hub")).toBeVisible();
    await expect(page.getByTestId("hub-card-employees")).toHaveCount(0);
    await expect(page.getByTestId("hub-card-sales")).toBeVisible();
    const res = await page.goto("/business/hr/employees");
    expect(res?.status()).toBe(403); // middleware rewrite → the 403 page (URL kept)
    await expect(page.getByTestId("forbidden")).toBeVisible();
    await expect(page.getByTestId("employee-table")).toHaveCount(0);
  });

  test("Sales overview (cross-khối :query) still opens for the Sales DIR", { tag: "@mock" }, async ({ page }) => {
    await loginSettled(page, "sales@abc.demo");
    await page.goto("/business/sales");
    await expect(page).toHaveURL(/\/business\/sales$/);
  });
});

test.describe("M6 · Reviewer", () => {
  test("Knowledge shows only the tabs the role may open; no 403 calls", { tag: "@mock" }, async ({ page }) => {
    await loginSettled(page, "reviewer@abc.demo");
    const errs = await backendErrors(page, async () => {
      await page.goto("/knowledge");
      await expect(page.getByTestId("knowledge-tab-documents")).toBeVisible();
      await expect(page.getByTestId("knowledge-tab-decisions")).toHaveCount(0);
      await expect(page.getByTestId("knowledge-tab-reports")).toHaveCount(0);
      await page.waitForLoadState("networkidle");
    });
    expect(errs).toEqual([]);
    await page.goto("/knowledge/decisions");
    await expect(page.getByTestId("forbidden")).toBeVisible();
  });
});
