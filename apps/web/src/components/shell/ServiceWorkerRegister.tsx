"use client";
import * as React from "react";

/**
 * Registers the PWA service worker (SCR-28, R-DEC-25) once, in the browser, in production only.
 * Non-breaking in dev (where Next's dev assets must not be intercepted) and where the API is
 * unavailable. Renders nothing.
 */
export function ServiceWorkerRegister() {
  React.useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    const register = () => navigator.serviceWorker.register("/sw.js").catch(() => {});
    if (document.readyState === "complete") register();
    else window.addEventListener("load", register, { once: true });
  }, []);
  return null;
}
