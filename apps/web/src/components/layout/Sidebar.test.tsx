/**
 * TC-UI-006 (part) — sidebar renders exactly the nav items each role is entitled to (06 §2.1),
 * driven by nav-config.ts `getNavItems`. Also checks the active-link `aria-current` contract.
 */
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../messages/vi.json";
import { ROLE_CODES, getNavItems } from "@/features/navigation/nav-config";
import { renderWithRole } from "@/test/render";
import { Sidebar } from "./Sidebar";

// next/navigation is a server/runtime module; provide the client hooks the Sidebar reads.
const pathnameRef = { current: "/dashboard" };
vi.mock("next/navigation", () => ({
  usePathname: () => pathnameRef.current,
}));

afterEach(cleanup);

const navLabels = viMessages.shell.nav;

describe("Sidebar per-role items (06 §2.1, nav-config.ts)", () => {
  for (const role of ROLE_CODES) {
    it(`renders exactly the entitled items for ${role}`, () => {
      pathnameRef.current = "/dashboard";
      renderWithRole(<Sidebar />, role);

      const nav = screen.getByRole("navigation", { name: navLabels.landmark });
      const links = within(nav).getAllByRole("link");
      const expected = getNavItems(role);

      expect(links).toHaveLength(expected.length);
      expected.forEach((item, index) => {
        expect(links[index]).toHaveAttribute("href", item.href);
        // Accessible name comes from the label text (kept in the DOM even in rail mode).
        expect(links[index]).toHaveAccessibleName(navLabels[item.id]);
      });
    });
  }

  it("marks the matching item with aria-current=page (active-link rule)", () => {
    pathnameRef.current = "/documents/abc-123";
    renderWithRole(<Sidebar />, "ROLE-01");

    const current = screen.getByRole("link", { current: "page" });
    expect(current).toHaveAttribute("href", "/documents");
  });

  it("hides items a role lacks (ROLE-03 has no inbox; ROLE-05 has no dashboard)", () => {
    pathnameRef.current = "/documents";
    const r3 = renderWithRole(<Sidebar />, "ROLE-03");
    expect(screen.queryByRole("link", { name: navLabels.inbox })).toBeNull();
    r3.unmount();

    renderWithRole(<Sidebar />, "ROLE-05");
    expect(screen.queryByRole("link", { name: navLabels.dashboard })).toBeNull();
    expect(screen.getByRole("link", { name: navLabels.schemas })).toBeInTheDocument();
  });
});
