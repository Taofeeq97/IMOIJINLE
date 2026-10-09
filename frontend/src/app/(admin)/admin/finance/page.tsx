"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ResponsiveTable } from "@/components/adaptive/responsive-table";
import { PageHeader } from "@/components/shared/page-header";
import { getAccessToken } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function FinancePage() {
  const { user, loading } = useAuth();
  const [overview, setOverview] = useState<Record<string, number | string> | null>(null);
  const [outstanding, setOutstanding] = useState<
    { invoice_id: string; user_email: string; description: string; balance_minor: number }[]
  >([]);
  const [tableLoading, setTableLoading] = useState(true);

  useEffect(() => {
    if (loading || !user) return;
    const headers = { Authorization: `Bearer ${getAccessToken() || ""}` };
    setTableLoading(true);
    void Promise.all([
      fetch(`${API_URL}/api/v1/finance/overview`, { headers, credentials: "include" }).then((r) => r.json()),
      fetch(`${API_URL}/api/v1/finance/outstanding`, { headers, credentials: "include" }).then((r) => r.json()),
    ])
      .then(([o, out]) => {
        setOverview(o);
        setOutstanding(Array.isArray(out) ? out : out.results || []);
      })
      .catch((err: Error) => toast.error(err.message))
      .finally(() => setTableLoading(false));
  }, [user, loading]);

  return (
    <>
      <PageHeader title="Finance" description="Collection overview and outstanding invoices." />
      {overview ? (
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Collected", overview.collected_minor],
            ["Outstanding", overview.outstanding_minor],
            ["Invoiced", overview.invoiced_minor],
            ["Success rate", `${overview.success_rate ?? 0}%`],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">{label}</p>
              <p className="mt-1 text-2xl font-semibold">
                {typeof value === "number" && label !== "Success rate"
                  ? `₦${(Number(value) / 100).toLocaleString()}`
                  : value}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mb-8 text-sm text-[var(--muted-foreground)]">Loading overview…</p>
      )}

      <ResponsiveTable
        title="Outstanding invoices"
        description="Balances still due from learners."
        loading={tableLoading}
        emptyMessage="No outstanding invoices"
        emptyDescription="Paid and settled invoices do not appear here."
        columns={[
          { id: "email", header: "Learner", priority: "high", cell: (r) => r.user_email },
          { id: "desc", header: "Description", priority: "medium", cell: (r) => r.description },
          {
            id: "balance",
            header: "Balance",
            priority: "high",
            align: "right",
            cell: (r) => `₦${(r.balance_minor / 100).toFixed(2)}`,
          },
        ]}
        data={outstanding.slice(0, 50)}
        getRowId={(r) => r.invoice_id}
      />
    </>
  );
}
