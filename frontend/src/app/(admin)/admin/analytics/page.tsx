"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { getAccessToken } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AnalyticsPage() {
  const [data, setData] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    void fetch(`${API_URL}/api/v1/analytics/overview`, {
      headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
      credentials: "include",
    })
      .then((r) => r.json())
      .then(setData)
      .catch((e: Error) => toast.error(e.message));
  }, []);

  return (
    <>
      <PageHeader title="Analytics" description="Enrollment and learning progress overview." />
      {data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(data).map(([k, v]) => (
            <div key={k} className="rounded-lg border p-4">
              <p className="text-xs uppercase text-[var(--muted-foreground)]">{k.replaceAll("_", " ")}</p>
              <p className="mt-1 text-2xl font-semibold">{v}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
      )}
    </>
  );
}
