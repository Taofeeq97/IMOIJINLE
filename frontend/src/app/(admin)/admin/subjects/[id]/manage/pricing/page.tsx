"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function PricingPage() {
  const params = useParams<{ id: string }>();
  const { refresh, markSaved } = useSubjectManage();
  const [mode, setMode] = useState("free");
  const [amount, setAmount] = useState("0");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void api
      .getPricing(params.id)
      .then((p) => {
        setMode(String(p.mode ?? "free"));
        setAmount(String(p.amount_kobo ?? 0));
      })
      .catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function save() {
    setSaving(true);
    try {
      await api.putPricing(params.id, {
        mode,
        amount_kobo: Number(amount) || 0,
        currency: "NGN",
      });
      markSaved();
      await refresh();
      toast.success("Pricing saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h2 className="font-display text-2xl">Access & pricing</h2>
      <p className="text-sm text-[var(--muted-foreground)]">
        Full Paystack class/subject fees land in M5. Configure mode here for the publish checklist.
      </p>
      <div className="space-y-1">
        <Label>Access mode</Label>
        <select
          className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="free">Free</option>
          <option value="class_fee">Included in class fee</option>
          <option value="paid">Separate subject fee</option>
        </select>
      </div>
      {mode === "paid" ? (
        <div className="space-y-1">
          <Label>Amount (kobo)</Label>
          <Input value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
      ) : null}
      <Button onClick={() => void save()} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
