"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApplicationItem } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

const STEPS = [
  { key: "submitted", label: "Applied" },
  { key: "account", label: "Account" },
  { key: "fee", label: "Pay fee" },
  { key: "review", label: "Under review" },
  { key: "admitted", label: "Admitted" },
] as const;

function stepIndex(status: string, feeAmount: number | null) {
  if (status === "admitted") return 4;
  if (["under_review", "fee_paid", "waitlisted"].includes(status)) return 3;
  if (status === "fee_pending") return 2;
  if (["account_active", "account_pending"].includes(status)) {
    return feeAmount && feeAmount > 0 ? 1 : 3;
  }
  if (status === "submitted") return 0;
  return 0;
}

function formatNaira(kobo: number) {
  return new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN" }).format(kobo / 100);
}

export default function PortalApplicationPage() {
  const params = useParams<{ id: string }>();
  const { user, loading } = useAuth();
  const router = useRouter();
  const [app, setApp] = useState<ApplicationItem | null>(null);
  const [paying, setPaying] = useState(false);

  async function load() {
    const data = await api.getPortalApplication(params.id);
    setApp(data);
  }

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [params.id, user, loading, router]);

  const activeStep = useMemo(
    () => (app ? stepIndex(app.status, app.fee_amount_kobo) : 0),
    [app],
  );

  async function payNow() {
    if (!app) return;
    setPaying(true);
    try {
      const idem = crypto.randomUUID();
      const pay = await api.payApplicationFee(app.id, idem);
      window.location.href = pay.authorization_url;
    } catch (err) {
      toast.error((err as ApiError).message ?? "Payment failed");
    } finally {
      setPaying(false);
    }
  }

  if (!app) {
    return <p className="p-8 text-sm text-[var(--muted-foreground)]">Loading application…</p>;
  }

  const needsFee =
    app.status === "fee_pending" &&
    (app.fee_amount_kobo ?? 0) > 0 &&
    app.fee_invoice_status !== "paid";

  return (
    <div className="mx-auto max-w-[900px] px-4 py-10">
      <PageHeader
        title={app.cohort_name}
        description={`Application for ${app.applicant_name}`}
        actions={
          <Button asChild variant="outline">
            <Link href="/portal">All applications</Link>
          </Button>
        }
      />

      <ol className="mb-8 grid gap-2 sm:grid-cols-5">
        {STEPS.map((step, idx) => (
          <li
            key={step.key}
            className={`rounded-md border px-3 py-2 text-center text-xs ${
              idx <= activeStep
                ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)]"
                : "border-[var(--border)] text-[var(--muted-foreground)]"
            }`}
          >
            {step.label}
            {idx < activeStep ? " ✓" : ""}
          </li>
        ))}
      </ol>

      <div className="space-y-4 rounded-lg border border-[var(--border)] bg-[var(--card)] p-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-[var(--muted-foreground)]">Status</span>
          <Badge>{app.status.replaceAll("_", " ")}</Badge>
        </div>

        {needsFee ? (
          <div className="space-y-3 rounded-md border border-dashed border-[var(--border)] p-4">
            <p className="font-medium">Application fee due</p>
            <p className="text-sm text-[var(--muted-foreground)]">
              {formatNaira(app.fee_amount_kobo ?? 0)} · Pay securely via Paystack
            </p>
            <Button onClick={() => void payNow()} disabled={paying}>
              {paying ? "Starting payment…" : "Pay now"}
            </Button>
          </div>
        ) : null}

        {app.fee_paid_at ? (
          <p className="text-sm text-[var(--muted-foreground)]">
            Fee paid {new Date(app.fee_paid_at).toLocaleString()}
          </p>
        ) : null}

        {app.status === "admitted" ? (
          <div className="space-y-2">
            <p className="text-sm">You have been admitted. Open My learning to start.</p>
            <Button asChild>
              <Link href="/learning">Go to My learning</Link>
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
