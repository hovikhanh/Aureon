import type { ReactElement, ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { RoleCode } from "@aureon/shared-types";
import { RoleProvider } from "@/features/navigation/role-context";
import messages from "../../messages/vi.json";

/** Render a component inside the i18n provider with real vi messages (06 §7.2 default locale). */
export function renderWithIntl(ui: ReactElement): RenderResult {
  return render(
    <NextIntlClientProvider locale="vi" messages={messages} timeZone="Asia/Ho_Chi_Minh">
      {ui}
    </NextIntlClientProvider>,
  );
}

/** Render inside i18n + a fixed active role (for shell/sidebar components). */
export function renderWithRole(ui: ReactNode, role: RoleCode): RenderResult {
  return render(
    <NextIntlClientProvider locale="vi" messages={messages} timeZone="Asia/Ho_Chi_Minh">
      <RoleProvider role={role}>{ui}</RoleProvider>
    </NextIntlClientProvider>,
  );
}
