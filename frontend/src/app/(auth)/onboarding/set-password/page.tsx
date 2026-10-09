"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

const schema = z
  .object({
    password: z.string().min(10, "At least 10 characters"),
    confirm: z.string().min(10),
  })
  .refine((v) => v.password === v.confirm, { message: "Passwords must match", path: ["confirm"] });

type FormValues = z.infer<typeof schema>;

function SetPasswordForm() {
  const search = useSearchParams();
  const router = useRouter();
  const { acceptSession } = useAuth();
  const token = search.get("token") ?? "";
  const applicationId = search.get("application_id") ?? "";
  const [email, setEmail] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
  });

  useEffect(() => {
    if (!token || !applicationId) {
      setChecking(false);
      return;
    }
    void api
      .verifyOnboarding(token, applicationId)
      .then((res) => setEmail(res.email))
      .catch((err: ApiError) => toast.error(err.message ?? "Invalid or expired link"))
      .finally(() => setChecking(false));
  }, [token, applicationId]);

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      const res = await api.setOnboardingPassword(token, applicationId, values.password);
      acceptSession(res.access, res.user);
      toast.success("Account ready");
      router.push(`/portal/applications/${applicationId}`);
    } catch (err) {
      toast.error((err as ApiError).message ?? "Could not set password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(31,92,77,0.12),_transparent_50%),var(--background)] px-4 py-10">
      <Card className="w-full max-w-md shadow-sm">
        <CardHeader>
          <CardTitle className="font-display text-2xl">Set your password</CardTitle>
          <CardDescription>
            {checking
              ? "Verifying your link…"
              : email
                ? `Continue as ${email}`
                : "This link is invalid or has expired. Request a new one from your success page."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {email ? (
            <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" autoComplete="new-password" {...form.register("password")} />
                {form.formState.errors.password ? (
                  <p className="text-xs text-[var(--destructive)]">
                    {form.formState.errors.password.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm">Confirm password</Label>
                <Input id="confirm" type="password" autoComplete="new-password" {...form.register("confirm")} />
                {form.formState.errors.confirm ? (
                  <p className="text-xs text-[var(--destructive)]">
                    {form.formState.errors.confirm.message}
                  </p>
                ) : null}
              </div>
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Saving…" : "Save and continue"}
              </Button>
            </form>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

export default function OnboardingSetPasswordPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-[var(--muted-foreground)]">Loading…</p>}>
      <SetPasswordForm />
    </Suspense>
  );
}
