"use client";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { MetricDetailContent } from "./MetricDetailContent";

const H1 = ({ className, children }: { className?: string; children?: ReactNode }) => <h1 className={className}>{children}</h1>;
const P = ({ className, children }: { className?: string; children?: ReactNode }) => <div className={className}>{children}</div>;

/** Full-page variant of the SCR-12 drill-down (alert notification target). */
export function MetricLandingView({ code }: { code: string }) {
  const t = useTranslations("metricDetail");
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4" data-testid="metric-landing" data-code={code}>
      <Link href="/home" className="flex w-fit items-center gap-1 text-sm text-primary hover:underline" data-testid="metric-landing-back">
        <ArrowLeft className="h-4 w-4" aria-hidden /> {t("backHome")}
      </Link>
      <section className="rounded-lg border bg-card p-5">
        <MetricDetailContent code={code} Title={H1} Desc={P} />
      </section>
    </div>
  );
}
