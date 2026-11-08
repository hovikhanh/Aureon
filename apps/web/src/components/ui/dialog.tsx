"use client";
import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40" />
      <DialogPrimitive.Content
        className={cn(
          // never taller than the viewport (U-08): the body scrolls, title and actions stay on screen
          "fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto overscroll-contain rounded-2xl border bg-card p-6 shadow-xl",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
export function DialogTitle({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className={cn("sticky top-0 z-10 -mx-6 -mt-6 bg-card px-6 pb-2 pt-6 text-lg font-semibold", className)} {...props} />;
}
/** Action row pinned to the bottom of a dialog that scrolls (long forms). */
export function DialogFooter({ className, ...props }: React.ComponentPropsWithoutRef<"div">) {
  return <div className={cn("sticky bottom-0 z-10 -mx-6 -mb-6 flex justify-end gap-2 border-t bg-card px-6 py-3", className)} {...props} />;
}
export function DialogDescription({ className, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>) {
  return <DialogPrimitive.Description className={cn("text-sm text-muted-foreground", className)} {...props} />;
}
