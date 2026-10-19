import type { ReactElement, ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RoleCode } from "@aureon/shared-types";
import { RoleProvider } from "@/features/navigation/role-context";
import messages from "../../messages/vi.json";

/** A fresh QueryClient per render with retries off, so tests never hang on query retries. */
function testQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
}

/** Render a component inside the i18n + TanStack Query providers with real vi messages. */
export function renderWithIntl(ui: ReactElement): RenderResult {
  return render(
    <QueryClientProvider client={testQueryClient()}>
      <NextIntlClientProvider locale="vi" messages={messages} timeZone="Asia/Ho_Chi_Minh">
        {ui}
      </NextIntlClientProvider>
    </QueryClientProvider>,
  );
}

/** Render inside i18n + Query + a fixed active role (for shell/sidebar components). */
export function renderWithRole(ui: ReactNode, role: RoleCode): RenderResult {
  return render(
    <QueryClientProvider client={testQueryClient()}>
      <NextIntlClientProvider locale="vi" messages={messages} timeZone="Asia/Ho_Chi_Minh">
        <RoleProvider role={role}>{ui}</RoleProvider>
      </NextIntlClientProvider>
    </QueryClientProvider>,
  );
}
