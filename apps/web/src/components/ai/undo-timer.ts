/**
 * UndoToast countdown (06 §5.1): 10 s, paused while the toast is hovered or focused; resumes with
 * the remaining time. Pure (injectable clock/timers) so it is unit-testable without a DOM.
 */
export const UNDO_TOAST_MS = 10_000;

export interface Timers { now: () => number; set: (fn: () => void, ms: number) => unknown; clear: (h: unknown) => void }
const realTimers: Timers = { now: () => Date.now(), set: (fn, ms) => setTimeout(fn, ms), clear: (h) => clearTimeout(h as ReturnType<typeof setTimeout>) };

export function createUndoTimer(onExpire: () => void, ms = UNDO_TOAST_MS, timers: Timers = realTimers) {
  let remaining = ms;
  let startedAt = 0;
  let handle: unknown = null;
  let done = false;
  const holds = new Set<string>();
  const run = () => {
    if (done || handle !== null || holds.size) return;
    startedAt = timers.now();
    handle = timers.set(() => { handle = null; done = true; onExpire(); }, remaining);
  };
  const stop = () => {
    if (handle === null) return;
    timers.clear(handle);
    handle = null;
    remaining = Math.max(0, remaining - (timers.now() - startedAt));
  };
  return {
    start: run,
    /** `hover` / `focus` holds — the countdown runs only when no hold is active. */
    pause: (why: string) => { holds.add(why); stop(); },
    resume: (why: string) => { holds.delete(why); run(); },
    cancel: () => { stop(); done = true; },
    remaining: () => (handle === null ? remaining : Math.max(0, remaining - (timers.now() - startedAt))),
    get done() { return done; },
  };
}
