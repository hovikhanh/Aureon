/** SCR-13 show/hide password toggle state (T-610c, 06 §8.2) — pure, unit-tested. */
export interface PasswordToggleState {
  inputType: "password" | "text";
  ariaPressed: boolean;
  labelKey: "auth.showPassword" | "auth.hidePassword";
}

export function passwordToggle(visible: boolean): PasswordToggleState {
  return visible
    ? { inputType: "text", ariaPressed: true, labelKey: "auth.hidePassword" }
    : { inputType: "password", ariaPressed: false, labelKey: "auth.showPassword" };
}
