import { describe, expect, it } from "vitest";
import { passwordToggle } from "./password-toggle";
import vi from "../../../messages/vi.json";
import en from "../../../messages/en.json";

/** T-610c / TC-M11-17: eye toggle flips the input type and aria-pressed together. */
describe("passwordToggle", () => {
  it("hidden → type=password, aria-pressed=false, label 'show'", () => {
    expect(passwordToggle(false)).toEqual({ inputType: "password", ariaPressed: false, labelKey: "auth.showPassword" });
  });

  it("visible → type=text, aria-pressed=true, label 'hide'", () => {
    expect(passwordToggle(true)).toEqual({ inputType: "text", ariaPressed: true, labelKey: "auth.hidePassword" });
  });

  it("has vi + en strings for both labels and the missing-password hint", () => {
    for (const k of ["showPassword", "hidePassword", "demoPasswordMissing"]) {
      expect(vi.auth, k).toHaveProperty(k);
      expect(en.auth, k).toHaveProperty(k);
    }
  });
});
