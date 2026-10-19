/**
 * T-222 — SCR-08 C4 PWA camera capture (06 §4.2, FR-DC-04, US-DC-004, TC-IDP-006, TC-UI-007).
 * getUserMedia + canvas are stubbed; we verify the capture → page list → submit flow, the
 * offline banner, and the unsupported-device fallback.
 */
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import viMessages from "../../../../messages/vi.json";
import { CameraCaptureC4 } from "./CameraCaptureC4";

function withIntl(ui: ReactElement) {
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages} timeZone="Asia/Ho_Chi_Minh">
      {ui}
    </NextIntlClientProvider>
  );
}

const fakeTrack = { stop: vi.fn() };
const fakeStream = { getTracks: () => [fakeTrack] } as unknown as MediaStream;

beforeEach(() => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn().mockResolvedValue(fakeStream) },
  });
  Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
  // jsdom <video> has no real dimensions; stub them so capture has a size.
  Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", { configurable: true, value: 1280 });
  Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", { configurable: true, value: 720 });
  HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
  HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/jpeg;base64,xxx");
  HTMLCanvasElement.prototype.toBlob = vi.fn((cb: BlobCallback) =>
    cb(new Blob(["x"], { type: "image/jpeg" })),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("TC-IDP-006 / TC-UI-007 CameraCaptureC4", () => {
  it("captures pages and submits them (3 photos → 3 pages)", async () => {
    const onSubmit = vi.fn();
    render(withIntl(<CameraCaptureC4 onSubmit={onSubmit} isSubmitting={false} />));

    // Open camera
    fireEvent.click(screen.getByText("Mở camera"));
    await waitFor(() => expect(screen.getByText("Chụp trang")).toBeInTheDocument());

    // Capture three pages
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        fireEvent.click(screen.getByText("Chụp trang"));
      });
    }
    await waitFor(() => expect(screen.getByText("Các trang đã chụp (3)")).toBeInTheDocument());

    // Submit
    fireEvent.click(screen.getByText("Gửi 3 trang"));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toHaveLength(3);
  });

  it("shows the offline banner when navigator is offline", async () => {
    Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
    render(withIntl(<CameraCaptureC4 onSubmit={vi.fn()} isSubmitting={false} />));
    await waitFor(() =>
      expect(screen.getByText(/Đang ngoại tuyến/)).toBeInTheDocument(),
    );
  });

  it("falls back gracefully when getUserMedia is unsupported", () => {
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
    render(withIntl(<CameraCaptureC4 onSubmit={vi.fn()} isSubmitting={false} />));
    expect(screen.getByText(/không hỗ trợ camera/i)).toBeInTheDocument();
  });

  it("disables submit until at least one page is captured", async () => {
    render(withIntl(<CameraCaptureC4 onSubmit={vi.fn()} isSubmitting={false} />));
    const submit = screen.getByText("Gửi 0 trang");
    expect(submit).toBeDisabled();
  });
});
