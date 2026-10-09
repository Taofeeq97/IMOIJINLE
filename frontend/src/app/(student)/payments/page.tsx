"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { getAccessToken } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Invoice = {
  id: string;
  description: string;
  status: string;
  amount_minor: number;
  currency: string;
};

export default function PaymentsPage() {
  const { user, loading } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  useEffect(() => {
    if (loading || !user) return;
    void fetch(`${API_URL}/api/v1/me/invoices`, {
      headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
      credentials: "include",
    })
      .then(async (r) => {
        if (!r.ok) throw new Error("Failed to load invoices");
        return r.json();
      })
      .then((data) => setInvoices(Array.isArray(data) ? data : data.results || []))
      .catch((err: Error) => toast.error(err.message));
  }, [user, loading]);

  async function pay(id: string) {
    try {
      const r = await fetch(`${API_URL}/api/v1/invoices/${id}/pay/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAccessToken() || ""}`,
          "Content-Type": "application/json",
        },
        body: "{}",
        credentials: "include",
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.message || "Payment failed");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="Payments" description="Outstanding invoices and history." />
      <ul className="space-y-3">
        {invoices.length === 0 ? (
          <li className="text-sm text-[var(--muted-foreground)]">No invoices yet.</li>
        ) : (
          invoices.map((inv) => (
            <li key={inv.id} className="flex items-center justify-between gap-3 rounded-lg border p-4">
              <div>
                <p className="font-medium">{inv.description || "Invoice"}</p>
                <p className="text-sm text-[var(--muted-foreground)]">
                  {(inv.amount_minor / 100).toFixed(2)} {inv.currency} · {inv.status}
                </p>
              </div>
              {inv.status !== "paid" && inv.status !== "void" ? (
                <Button size="sm" onClick={() => void pay(inv.id)}>
                  Pay now
                </Button>
              ) : null}
            </li>
          ))
        )}
      </ul>
    </>
  );
}
