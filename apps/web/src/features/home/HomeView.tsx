"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ExecutiveView } from "./ExecutiveView";
import { DepartmentView } from "./DepartmentView";
import { EmployeeView } from "./EmployeeView";
import { levelsFor, type Level } from "./levels";

/** SCR-40 `/home` — chọn cấp theo role (R-DEC-85). CEO/DIR mặc định Executive + chuyển
 * Department; MGR mặc định Department; còn lại Employee. Reviewer/Admin đã redirect ở page. */
export function HomeView({ role }: { role: string }) {
  const t = useTranslations("home");
  const levels = levelsFor(role);
  const [level, setLevel] = useState<Level>(levels[0] ?? "employee");
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        {levels.length > 1 && (
          <div className="flex gap-1 rounded-md border p-1" role="tablist" data-testid="level-tabs">
            {levels.map((l) => (
              <Button key={l} size="sm" variant={l === level ? "default" : "ghost"} role="tab"
                aria-selected={l === level} data-testid={`level-${l}`} onClick={() => setLevel(l)}>
                {t(`level.${l}`)}
              </Button>
            ))}
          </div>
        )}
      </div>
      {level === "executive" && <ExecutiveView />}
      {level === "department" && <DepartmentView />}
      {level === "employee" && <EmployeeView />}
    </div>
  );
}
