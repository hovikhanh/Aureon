/**
 * T-222 (DEC-123 hướng A) — C4 client image helpers: blur scoring (IDP-E05) and the
 * multi-page PDF merge (FR-DC-04). Blur scoring is pure math over RGBA bytes, so it is
 * tested without the DOM.
 */
import { describe, expect, it } from "vitest";
import { BLUR_THRESHOLD, isTooBlurry, laplacianVariance } from "./c4-image";

function solidImage(width: number, height: number, gray: number): Uint8ClampedArray {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < data.length; i += 4) {
    data[i] = gray;
    data[i + 1] = gray;
    data[i + 2] = gray;
    data[i + 3] = 255;
  }
  return data;
}

function checkerboard(width: number, height: number): Uint8ClampedArray {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const v = (x + y) % 2 === 0 ? 0 : 255;
      const p = (y * width + x) * 4;
      data[p] = v;
      data[p + 1] = v;
      data[p + 2] = v;
      data[p + 3] = 255;
    }
  }
  return data;
}

describe("laplacianVariance (blur score)", () => {
  it("returns ~0 for a flat (perfectly smooth → 'blurry') image", () => {
    const score = laplacianVariance(solidImage(16, 16, 128), 16, 16);
    expect(score).toBeCloseTo(0, 5);
  });

  it("returns a high score for a sharp high-contrast pattern", () => {
    const score = laplacianVariance(checkerboard(16, 16), 16, 16);
    expect(score).toBeGreaterThan(BLUR_THRESHOLD);
  });

  it("guards against images that are too small to score", () => {
    expect(laplacianVariance(solidImage(2, 2, 100), 2, 2)).toBe(0);
  });
});

describe("isTooBlurry (IDP-E05)", () => {
  it("flags a score below the threshold", () => {
    expect(isTooBlurry(10)).toBe(true);
    expect(isTooBlurry(BLUR_THRESHOLD - 1)).toBe(true);
  });

  it("accepts a score at or above the threshold", () => {
    expect(isTooBlurry(BLUR_THRESHOLD)).toBe(false);
    expect(isTooBlurry(500)).toBe(false);
  });
});
