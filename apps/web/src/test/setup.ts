// Vitest + Testing Library setup (T-108, DEC-117).
// Registers jest-dom matchers (toBeInTheDocument, toHaveAttribute, ...) for jsdom tests.
import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom does not implement the 2D canvas context. axe-core's icon-ligature heuristic
// calls getContext() during a11y scans and, when it throws "Not implemented", the
// rejection leaks across the parallel worker and randomly flakes a neighbouring test.
// Returning a minimal stub keeps axe deterministic without pulling in the native canvas
// package. This affects tests only (T-220 added SourceViewer/image-heavy a11y scans).
if (typeof HTMLCanvasElement !== "undefined") {
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
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
