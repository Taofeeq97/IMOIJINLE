"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type PublicCohort } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name"),
  email: z.string().email(),
  phone: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function formatNaira(kobo: number) {
  return new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN" }).format(kobo / 100);
}

function ApplyInner() {
  const params = useParams<{ cohortSlug: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const [cohort, setCohort] = useState<PublicCohort | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const successId = search.get("application_id");
  const successEmail = search.get("email");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", phone: "" },
  });

  useEffect(() => {
    void api
      .getPublicCohort(params.cohortSlug)
      .then(setCohort)
      .catch((err: ApiError) => toast.error(err.message ?? "Cohort not found"))
      .finally(() => setLoading(false));
  }, [params.cohortSlug]);

  const feeLabel = useMemo(() => {
    if (!cohort) return "";
    return cohort.application_fee_kobo > 0 ? formatNaira(cohort.application_fee_kobo) : "Free";
  }, [cohort]);

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    try {
      const res = await api.submitApplication(params.cohortSlug, {
        full_name: values.full_name,
        email: values.email,
        phone: values.phone,
      });
      toast.success("Application submitted");
      router.push(
        `/apply/${params.cohortSlug}?application_id=${res.application_id}&email=${encodeURIComponent(res.email)}`,
      );
    } catch (err) {
      toast.error((err as ApiError).message ?? "Could not submit");
    } finally {
      setSubmitting(false);
    }
  }

  async function resend() {
    if (!successId) return;
    try {
      await api.resendOnboarding(successId);
      toast.success("If eligible, a new link was sent");
    } catch (err) {
      toast.error((err as ApiError).message ?? "Could not resend");
    }
  }

  async function changeEmail() {
    if (!successId) return;
    const email = window.prompt("New email address");
    if (!email) return;
    try {
      await api.changeApplicationEmail(successId, email);
      toast.success("Email updated — check your inbox");
      router.replace(
        `/apply/${params.cohortSlug}?application_id=${successId}&email=${encodeURIComponent(email)}`,
      );
    } catch (err) {
      toast.error((err as ApiError).message ?? "Could not update email");
    }
  }

  if (loading) {
    return <p className="text-sm text-[var(--muted-foreground)]">Loading cohort…</p>;
  }

  if (!cohort) {
    return (
      <>
        <PageHeader title="Cohort not found" description="Check the apply link and try again." />
        <Button asChild variant="outline">
          <Link href="/cohorts">Browse cohorts</Link>
        </Button>
      </>
    );
  }

  if (successId && successEmail) {
    return (
      <>
        <PageHeader
          title="Check your email"
          description="We sent a secure link to set up your account and continue."
        />
        <div className="mx-auto max-w-xl space-y-6">
          <p className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-6 text-center">
            Link sent to{" "}
            <span className="font-semibold text-[var(--foreground)]">{successEmail}</span>
          </p>
          <ol className="space-y-2 text-sm text-[var(--muted-foreground)]">
            <li>1. Check email → open “Set up your account”</li>
            <li>2. Set password → sign in</li>
            <li>3. Pay application fee (if required)</li>
            <li>4. Wait for admission</li>
          </ol>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => void resend()}>
              Resend link
            </Button>
            <Button type="button" variant="secondary" onClick={() => void changeEmail()}>
              Change email
            </Button>
            <Button asChild>
              <Link href="/login">Already have an account? Sign in</Link>
            </Button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={cohort.name}
        description={
          cohort.status === "applications_open"
            ? `Applications open · Fee ${feeLabel}`
            : `Status: ${cohort.status}`
        }
      />
      <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <p className="text-sm leading-relaxed text-[var(--muted-foreground)]">
            Apply to join this intake. After you submit, we email a one-time link (72 hours) to set
            your password and continue on your applicant portal.
          </p>
          {cohort.classes.length > 0 ? (
            <div>
              <h2 className="mb-2 font-display text-lg">Classes offered</h2>
              <ul className="space-y-2">
                {cohort.classes.map((c) => (
                  <li
                    key={c.id}
                    className="rounded-md border border-[var(--border)] px-3 py-2 text-sm"
                  >
                    {c.name}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        <form
          className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5"
          onSubmit={form.handleSubmit(onSubmit)}
        >
          <h2 className="font-display text-xl">Apply now</h2>
          <div className="space-y-2">
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" {...form.register("full_name")} />
            {form.formState.errors.full_name ? (
              <p className="text-xs text-[var(--destructive)]">
                {form.formState.errors.full_name.message}
              </p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
            {form.formState.errors.email ? (
              <p className="text-xs text-[var(--destructive)]">{form.formState.errors.email.message}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Phone (optional)</Label>
            <Input id="phone" {...form.register("phone")} />
          </div>
          <p className="text-xs text-[var(--muted-foreground)]">Application fee: {feeLabel}</p>
          <Button type="submit" disabled={submitting || cohort.status !== "applications_open"}>
            {submitting ? "Submitting…" : "Submit application"}
          </Button>
        </form>
      </div>
    </>
  );
}

export default function ApplyPage() {
  return (
    <Suspense fallback={<p className="text-sm text-[var(--muted-foreground)]">Loading…</p>}>
      <ApplyInner />
    </Suspense>
  );
}
