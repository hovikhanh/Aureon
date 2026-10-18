/**
 * Icons for sidebar items (T-108). Kept separate from nav-config.ts so that file stays a pure
 * role/route/i18n source with no React/lucide dependency. Keyed by `NavItemId` (06 §6.1: lucide
 * is the default icon set per DEC-117).
 */
import { FileText, LayoutDashboard, ListChecks, ScrollText, Table2, Upload, type LucideIcon } from "lucide-react";
import type { NavItemId } from "./nav-config";

export const NAV_ICONS: Record<NavItemId, LucideIcon> = {
  dashboard: LayoutDashboard,
  inbox: ListChecks,
  documents: FileText,
  upload: Upload,
  schemas: Table2,
  audit: ScrollText,
};
