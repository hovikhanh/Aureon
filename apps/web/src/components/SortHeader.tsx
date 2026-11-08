"use client";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { ariaSort, type SortState } from "@/lib/sort";
import { cn } from "@/lib/utils";

/** Column header that sorts on click: `aria-sort` on the `th`, a real button inside for the keyboard. */
export function SortHeader({ field, label, sort, onSort, className }: { field: string; label: string; sort: SortState; onSort: (field: string) => void; className?: string }) {
  const state = ariaSort(sort, field);
  const Icon = state === "none" ? ChevronsUpDown : state === "ascending" ? ArrowUp : ArrowDown;
  return (
    <th scope="col" aria-sort={state} className={cn("px-3 py-2 font-medium", className)}>
      <button type="button" onClick={() => onSort(field)} className={cn("inline-flex items-center gap-1 hover:text-foreground", state !== "none" && "text-foreground")} data-testid={`sort-${field}`}>
        {label}<Icon className="h-3.5 w-3.5" aria-hidden />
      </button>
    </th>
  );
}
