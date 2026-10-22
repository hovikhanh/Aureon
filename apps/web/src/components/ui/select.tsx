import * as React from "react";
import { cn } from "@/lib/utils";

/** Native select styled like shadcn (keyboard/a11y for free). */
export const NativeSelect = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, ...props }, ref) => (
    <select ref={ref} className={cn("h-10 rounded border bg-card px-3 text-sm", className)} {...props} />
  ),
);
NativeSelect.displayName = "NativeSelect";
