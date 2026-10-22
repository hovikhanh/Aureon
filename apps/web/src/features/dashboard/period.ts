"use client";
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { DEFAULT_PERIOD } from "./pillars";

/** T-510 period picker: 4 choices relative to the business date (DEMO_REFERENCE_DATE in demo). */
export type PeriodChoice = "thisMonth" | "lastMonth" | "q3" | "q4";
export const PERIOD_CHOICES: readonly PeriodChoice[] = ["thisMonth", "lastMonth", "q3", "q4"];

const PERIOD_RE = /^\d{4}-(0[1-9]|1[0-2]|Q[1-4])$/;

export function referenceDate(): Date {
  const raw = process.env.NEXT_PUBLIC_DEMO_REFERENCE_DATE;
  const d = raw ? new Date(`${raw}T00:00:00Z`) : new Date();
  return Number.isNaN(d.getTime()) ? new Date() : d;
}

const ym = (y: number, m0: number) => `${y}-${String(m0 + 1).padStart(2, "0")}`;

export function periodFor(choice: PeriodChoice, ref: Date = referenceDate()): string {
  const y = ref.getUTCFullYear();
  const m = ref.getUTCMonth();
  switch (choice) {
    case "thisMonth":
      return ym(y, m);
    case "lastMonth":
      return m === 0 ? ym(y - 1, 11) : ym(y, m - 1);
    case "q3":
      return `${y}-Q3`;
    case "q4":
      return `${y}-Q4`;
  }
}

export function choiceOf(period: string, ref: Date = referenceDate()): PeriodChoice | null {
  return PERIOD_CHOICES.find((c) => periodFor(c, ref) === period) ?? null;
}

export function isPeriod(value: string | null | undefined): value is string {
  return !!value && PERIOD_RE.test(value);
}

/** Selected period lives in the URL (`?period=`) so drill-down links and reloads keep it. */
export function usePeriod(): { period: string; setPeriod: (p: string) => void; withPeriod: (href: string) => string } {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const raw = params.get("period");
  const period = isPeriod(raw) ? raw : DEFAULT_PERIOD;
  const setPeriod = React.useCallback(
    (p: string) => {
      const next = new URLSearchParams(params.toString());
      if (p === DEFAULT_PERIOD) next.delete("period");
      else next.set("period", p);
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );
  const withPeriod = React.useCallback(
    (href: string) => (period === DEFAULT_PERIOD ? href : `${href}?period=${period}`),
    [period],
  );
  return { period, setPeriod, withPeriod };
}
