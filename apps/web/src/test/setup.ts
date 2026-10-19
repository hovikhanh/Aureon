// Vitest + Testing Library setup (T-108, DEC-117).
// Registers jest-dom matchers (toBeInTheDocument, toHaveAttribute, ...) for jsdom tests.
import "@testing-library/jest-dom/vitest";
import { beforeEach } from "vitest";

// jsdom does not implement the 2D canvas context. axe-core's icon-ligature heuristic
// calls getContext() during a11y scans and, when it throws "Not implemented", the
// rejection leaks across the parallel worker and randomly flakes a neighbouring test.
// Returning a minimal stub keeps axe deterministic without pulling in the native canvas
// package. Re-installed before EVERY test so a per-file vi.restoreAllMocks() (e.g. the
// C4 camera suite) cannot revert it and reintroduce the flake. Tests only.
function installCanvasStub() {
  if (typeof HTMLCanvasElement === "undefined") return;
  HTMLCanvasElement.prototype.getContext = (() => ({
    measureText: () => ({ width: 0 }),
    fillText: () => {},
    getImageData: () => ({ data: new Uint8ClampedArray() }),
    fillRect: () => {},
    clearRect: () => {},
    drawImage: () => {},
    beginPath: () => {},
    closePath: () => {},
    save: () => {},
    restore: () => {},
  })) as unknown as HTMLCanvasElement["getContext"];
}

installCanvasStub();
beforeEach(installCanvasStub);
