"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { safeCallback } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Eye, EyeOff } from "lucide-react";
import { DEMO_ACCOUNTS, demoTestId } from "@/lib/demo-accounts";
import { fetchDemoPassword } from "./demo-autofill";
import { passwordToggle } from "./password-toggle";

const KNOWN_ERRORS = ["INVALID_CREDENTIALS", "RATE_LIMIT_EXCEEDED", "UNAUTHENTICATED"] as const;

export function LoginForm({ demoMode }: { demoMode: boolean }) {
  const t = useTranslations();
  const params = useSearchParams();
  const [error, setError] = React.useState<string | null>(null);
  const [picked, setPicked] = React.useState("");
  const [loadingDemo, setLoadingDemo] = React.useState(false);
  const [passwordMissing, setPasswordMissing] = React.useState(false);
  const [showPassword, setShowPassword] = React.useState(false);
  const toggle = passwordToggle(showPassword);
  const schema = React.useMemo(
    () =>
      z.object({
        email: z.string().email(t("auth.emailInvalid")),
        password: z.string().min(1, t("auth.passwordRequired")),
      }),
    [t],
  );
  type Values = z.infer<typeof schema>;
  const { register, handleSubmit, setValue, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const messageFor = (code: string) =>
    (KNOWN_ERRORS as readonly string[]).includes(code) ? t(`errors.${code}` as "errors.generic") : t("errors.generic");

  /** The password is a real form value (R-DEC-28) → `demo: "false"`; lib/auth keeps `demo: "true"` as fallback. */
  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    const res = await signIn("credentials", { email: values.email, password: values.password, demo: "false", redirect: false });
    if (!res || res.error) {
      setError(messageFor(res?.error ?? "INTERNAL_ERROR"));
      return;
    }
    window.location.assign(safeCallback(params.get("callbackUrl"), window.location.origin));
  });

  /** Pick a demo account → fill BOTH fields with real values; the user reviews and submits. */
  async function pickDemo(email: string) {
    setPicked(email);
    setPasswordMissing(false);
    if (!email) return;
    setLoadingDemo(true);
    setValue("email", email, { shouldValidate: true });
    setValue("password", "");
    const password = await fetchDemoPassword(email);
    setLoadingDemo(false);
    if (password) setValue("password", password, { shouldValidate: true });
    else setPasswordMissing(true);
  }

  const busy = loadingDemo || formState.isSubmitting;

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-label={t("auth.title")}>
      {demoMode && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="demo-account">{t("auth.demoAccounts")}</Label>
          <NativeSelect
            id="demo-account"
            data-testid="demo-account"
            value={picked}
            disabled={formState.isSubmitting}
            aria-describedby="demo-hint"
            onChange={(e) => void pickDemo(e.target.value)}
            className="w-full"
          >
            <option value="">{t("auth.demoPick")}</option>
            {DEMO_ACCOUNTS.map((a) => (
              <option key={a.email} value={a.email} data-testid={demoTestId(a.email)}>
                {`${t(`role.${a.role}`)}${a.pillar ? ` (${a.pillar})` : ""} — ${a.email}`}
              </option>
            ))}
          </NativeSelect>
          <p id="demo-hint" className="text-xs text-muted-foreground" aria-live="polite">
            {loadingDemo ? t("auth.demoLoading") : t("auth.demoHint")}
          </p>
          {passwordMissing && (
            <p data-testid="demo-password-missing" role="status" className="text-xs text-warning">
              {t("auth.demoPasswordMissing")}
            </p>
          )}
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">{t("auth.email")}</Label>
        <Input id="email" type="email" autoComplete="username" aria-invalid={!!formState.errors.email} {...register("email")} />
        {formState.errors.email && <p className="text-xs text-danger">{formState.errors.email.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">{t("auth.password")}</Label>
        <div className="relative">
          <Input
            id="password"
            type={toggle.inputType}
            autoComplete="current-password"
            aria-invalid={!!formState.errors.password}
            className="h-11 pr-12"
            {...register("password", { onChange: () => setPasswordMissing(false) })}
          />
          <button
            type="button"
            data-testid="toggle-password"
            aria-label={t(toggle.labelKey)}
            aria-pressed={toggle.ariaPressed}
            aria-controls="password"
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {showPassword ? <EyeOff className="h-5 w-5" aria-hidden /> : <Eye className="h-5 w-5" aria-hidden />}
          </button>
        </div>
        {formState.errors.password && <p className="text-xs text-danger">{formState.errors.password.message}</p>}
      </div>
      {error && (
        <p role="alert" data-testid="login-error" className="rounded border border-danger bg-danger-subtle px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy} className="mt-2">
        {formState.isSubmitting ? t("auth.signingIn") : t("buttons.login")}
      </Button>
    </form>
  );
}
