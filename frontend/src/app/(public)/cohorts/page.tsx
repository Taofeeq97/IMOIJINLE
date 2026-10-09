"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { api, type Cohort } from "@/lib/api/client";

export default function CohortsPublicPage() {
  const [rows, setRows] = useState<Cohort[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const data = await api.listPublicCohorts();
        setRows(data.results);
      } catch {
        setRows([]);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <>
      <PageHeader
        title="Cohorts"
        description="Academic sessions open for learning and applications."
      />
      {loading ? (
        <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No open cohorts yet"
          description="Check back when applications open for a new academic session."
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {rows.map((c) => (
            <li key={c.id} className="rounded-[var(--radius)] border bg-[var(--card)] p-5">
              <div className="flex items-start justify-between gap-3">
                <h2 className="font-display text-xl font-semibold">{c.name}</h2>
                <Badge>{c.status.replaceAll("_", " ")}</Badge>
              </div>
              {c.status === "applications_open" ? (
                <Link
                  href={c.public_apply_path}
                  className="mt-4 inline-flex text-sm font-medium text-[var(--primary)] underline"
                >
                  Apply now
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
