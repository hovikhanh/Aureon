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
import { DEMO_ACCOUNTS } from "@/lib/demo-accounts";

const KNOWN_ERRORS = ["INVALID_CREDENTIALS", "RATE_LIMIT_EXCEEDED", "UNAUTHENTICATED"] as const;

export function LoginForm({ demoMode }: { demoMode: boolean }) {
  const t = useTranslations();
  const params = useSearchParams();
  const [error, setError] = React.useState<string | null>(null);
  const [demoPicked, setDemoPicked] = React.useState(false);
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

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    const res = await signIn("credentials", {
      email: values.email,
      password: values.password,
      demo: demoPicked && !values.password ? "true" : "false",
      redirect: false,
    });
    if (!res || res.error) {
      setError(messageFor(res?.error ?? "INTERNAL_ERROR"));
      return;
    }
    window.location.assign(safeCallback(params.get("callbackUrl"), window.location.origin));
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4" aria-label={t("auth.title")}>
      {demoMode && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="demo">{t("auth.demoAccounts")}</Label>
          <NativeSelect
            id="demo"
            data-testid="demo-select"
            defaultValue=""
            onChange={(e) => {
              const email = e.target.value;
              if (!email) return;
              setDemoPicked(true);
              setValue("email", email, { shouldValidate: true });
              setValue("password", "");
            }}
          >
            <option value="">—</option>
            {DEMO_ACCOUNTS.map((a) => (
              <option key={a.email} value={a.email}>
                {t(`demoAccount.${a.labelKey}`)} — {a.email}
              </option>
            ))}
          </NativeSelect>
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
