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
import { DEMO_ACCOUNTS, demoTestId, type DemoAccount } from "@/lib/demo-accounts";

const KNOWN_ERRORS = ["INVALID_CREDENTIALS", "RATE_LIMIT_EXCEEDED", "UNAUTHENTICATED"] as const;

export function LoginForm({ demoMode }: { demoMode: boolean }) {
  const t = useTranslations();
  const params = useSearchParams();
  const [error, setError] = React.useState<string | null>(null);
  const [demoPicked, setDemoPicked] = React.useState(false);
  const [pending, setPending] = React.useState<string | null>(null);
  const schema = React.useMemo(
    () =>
      z.object({
        email: z.string().email(t("auth.emailInvalid")),
        password: demoPicked ? z.string() : z.string().min(1, t("auth.passwordRequired")),
      }),
    [t, demoPicked],
  );
  type Values = z.infer<typeof schema>;
  const { register, handleSubmit, setValue, formState } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const messageFor = (code: string) =>
    (KNOWN_ERRORS as readonly string[]).includes(code) ? t(`errors.${code}` as "errors.generic") : t("errors.generic");

  async function submitCredentials(email: string, password: string, demo: boolean) {
    setError(null);
    const res = await signIn("credentials", { email, password, demo: demo ? "true" : "false", redirect: false });
    if (!res || res.error) {
      setError(messageFor(res?.error ?? "INTERNAL_ERROR"));
      return;
    }
    window.location.assign(safeCallback(params.get("callbackUrl"), window.location.origin));
  }

  const onSubmit = handleSubmit((values) => submitCredentials(values.email, values.password, demoPicked && !values.password));

  /** One click = fill the form with the account and sign in; the password stays server-side. */
  async function quickLogin(account: DemoAccount) {
    setDemoPicked(true);
    setPending(account.email);
    setValue("email", account.email, { shouldValidate: true });
    setValue("password", "");
    await submitCredentials(account.email, "", true);
    setPending(null);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-label={t("auth.title")}>
      {demoMode && (
        <div className="flex flex-col gap-1.5">
          <span id="demo-label" className="text-sm font-medium">
            {t("auth.demoAccounts")}
          </span>
          <div role="group" aria-labelledby="demo-label" data-testid="demo-logins" className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <Button
                key={a.email}
                type="button"
                variant="outline"
                data-testid={demoTestId(a.email)}
                disabled={pending !== null || formState.isSubmitting}
                onClick={() => void quickLogin(a)}
                className="h-auto flex-col items-start gap-0.5 px-3 py-2 text-left"
              >
                <span className="flex w-full items-center gap-1.5 text-sm font-medium">
                  {t(`demoAccount.${a.labelKey}`)}
                  <span className="rounded bg-muted px-1 text-[10px] font-normal text-muted-foreground">
                    {t(`role.${a.role}`)}
                    {a.pillar ? ` · ${t(`pillar.${a.pillar}.name`)}` : ""}
                  </span>
                </span>
                <span className="w-full truncate text-xs font-normal text-muted-foreground">
                  {pending === a.email ? t("auth.signingIn") : a.email}
                </span>
              </Button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">{t("auth.demoHint")}</p>
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">{t("auth.email")}</Label>
        <Input id="email" type="email" autoComplete="username" aria-invalid={!!formState.errors.email} {...register("email")} />
        {formState.errors.email && <p className="text-xs text-danger">{formState.errors.email.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">{t("auth.password")}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={!!formState.errors.password}
          {...register("password", { onChange: () => setDemoPicked(false) })}
        />
        {formState.errors.password && <p className="text-xs text-danger">{formState.errors.password.message}</p>}
      </div>
      {error && (
        <p role="alert" data-testid="login-error" className="rounded border border-danger bg-danger-subtle px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" disabled={formState.isSubmitting} className="mt-2">
        {formState.isSubmitting ? t("auth.signingIn") : t("buttons.login")}
      </Button>
    </form>
  );
}
