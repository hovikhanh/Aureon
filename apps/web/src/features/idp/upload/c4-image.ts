import { jsPDF } from "jspdf";
import type { CapturedPage } from "./CameraCaptureC4";

/**
 * C4 client-side image helpers (T-222, FR-DC-04, IDP-E05; DEC-123 hướng A).
 * - Blur scoring runs fully on the client (IDP-E05: "blur score phía client") with a pure
 *   variance-of-Laplacian over the grayscale image — no image library, unit-testable.
 * - Merging stitches the captured JPEG pages into ONE multi-page PDF via jsPDF so the backend
 *   receives a single multi-page document (FR-DC-04 "gộp ảnh thành một tài liệu nhiều trang"),
 *   without changing the EP-20 contract (still one file per request).
 */

/** Below this variance-of-Laplacian the photo is considered too blurry (IDP-E05). */
export const BLUR_THRESHOLD = 100;

/**
 * Variance of the Laplacian on a grayscale version of the image. Higher = sharper.
 * Operates on raw RGBA bytes so it is independent of the DOM/Canvas and easy to test.
 */
export function laplacianVariance(data: Uint8ClampedArray, width: number, height: number): number {
  if (width < 3 || height < 3) return 0;
  // Grayscale (luma) buffer.
  const gray = new Float64Array(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p += 1) {
    gray[p] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
  }
  // 4-neighbour Laplacian over the interior; collect values for mean/variance.
  let sum = 0;
  let sumSq = 0;
  let n = 0;
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x;
      const lap =
        gray[idx - 1] +
        gray[idx + 1] +
        gray[idx - width] +
        gray[idx + width] -
        4 * gray[idx];
      sum += lap;
      sumSq += lap * lap;
      n += 1;
    }
  }
  if (n === 0) return 0;
  const mean = sum / n;
  return sumSq / n - mean * mean;
}

/** IDP-E05: the client flags a photo for re-capture when its sharpness is below threshold. */
export function isTooBlurry(score: number, threshold: number = BLUR_THRESHOLD): boolean {
  return score < threshold;
}

/** Compute a blur score from a <canvas> 2D context (reads the whole frame). */
export function blurScoreFromContext(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
): number {
  const { data } = ctx.getImageData(0, 0, width, height);
  return laplacianVariance(data, width, height);
}

/** Natural size of a JPEG/PNG data URL. */
function imageSize(dataUrl: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => reject(new Error("image load failed"));
    img.src = dataUrl;
  });
}

/**
 * Merge captured pages into one multi-page PDF File. Each page is scaled to fit an A4 page
 * while preserving aspect ratio and centred. Returns a `File` ready for EP-20 (channel=C4).
 */
export async function mergePagesToPdf(
  pages: CapturedPage[],
  filename: string,
): Promise<File> {
  if (pages.length === 0) throw new Error("no pages to merge");
  const pdf = new jsPDF({ unit: "pt", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();

  for (let i = 0; i < pages.length; i += 1) {
    const { dataUrl } = pages[i];
    if (i > 0) pdf.addPage();
    const { width, height } = await imageSize(dataUrl);
    const scale = Math.min(pageW / width, pageH / height);
    const w = width * scale;
    const h = height * scale;
    const x = (pageW - w) / 2;
    const y = (pageH - h) / 2;
    pdf.addImage(dataUrl, "JPEG", x, y, w, h);
  }

  const blob = pdf.output("blob");
  return new File([blob], filename, { type: "application/pdf" });
}
