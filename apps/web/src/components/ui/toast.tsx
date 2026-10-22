"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

type Toast = { id: number; message: string; tone: "success" | "danger" | "info" };
type Ctx = { push: (message: string, tone?: Toast["tone"]) => void };
const ToastCtx = React.createContext<Ctx>({ push: () => undefined });

/** Toast host (mounted in the root layout, so toasts survive client-side navigation). */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<Toast[]>([]);
  const push = React.useCallback((message: string, tone: Toast["tone"] = "success") => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs, { id, message, tone }]);
    window.setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 6000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              "rounded-lg border px-4 py-3 text-sm shadow-lg",
              t.tone === "success" && "border-success bg-success-subtle text-success",
              t.tone === "danger" && "border-danger bg-danger-subtle text-danger",
              t.tone === "info" && "bg-card",
            )}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => React.useContext(ToastCtx);

