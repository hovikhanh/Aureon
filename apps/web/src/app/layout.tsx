import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { Providers } from "./providers";
import "./globals.css";

// `preload: false` — the font ships 4 weights × (latin + latin-ext + vietnamese) `@font-face`
// rules; with preload on, next/font emits a <link rel="preload"> for all 8 latin+vietnamese
// woff2, but a given first paint consumes only a couple of them, so the browser warns
// "preloaded ... was not used within a few seconds". Dropping the eager preload removes the
// warning; fonts still load on demand via the generated @font-face + `display: swap`, so the
// Vietnamese subset and the design are unchanged.
const font = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-be-vietnam",
  display: "swap",
  preload: false,
});

export const metadata: Metadata = { title: "Aureon", description: "Digital Chief of Staff" };
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  return (
    <html lang={locale} className={font.variable}>
      <body className="min-h-dvh font-sans antialiased">
        <NextIntlClientProvider locale={locale} messages={messages} timeZone="Asia/Ho_Chi_Minh">
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
