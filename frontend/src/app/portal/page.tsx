"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type ApplicationItem } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

function statusLabel(status: string) {
  return status.replaceAll("_", " ");
}

export default function PortalPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<ApplicationItem[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    void api
      .listPortalApplications()
      .then(setItems)
      .catch((err: ApiError) => toast.error(err.message))
      .finally(() => setReady(true));
  }, [user, loading, router]);

  if (loading || !ready) {
    return <p className="p-8 text-sm text-[var(--muted-foreground)]">Loading…</p>;
  }

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-10">
      <PageHeader
        title="My applications"
        description="Track status, pay fees, and continue after admission."
        actions={
          <Button asChild variant="outline">
            <Link href="/learning">My learning</Link>
          </Button>
        }
      />
      {items.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Open a cohort apply link to submit your first application."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((app) => (
            <li
              key={app.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3"
            >
              <div>
                <p className="font-medium">{app.cohort_name}</p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Submitted {new Date(app.submitted_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge>{statusLabel(app.status)}</Badge>
                <Button asChild size="sm">
                  <Link href={`/portal/applications/${app.id}`}>Open</Link>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
