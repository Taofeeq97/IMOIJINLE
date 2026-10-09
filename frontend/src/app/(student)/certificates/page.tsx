"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";
import { api, type IssuedCertificate } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function StudentCertificatesPage() {
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<IssuedCertificate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    api
      .myCertificates()
      .then(setItems)
      .catch((err: ApiError) => toast.error(err.message ?? "Failed to load"))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  async function copyLink(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Verify link copied");
    } catch {
      toast.error("Could not copy");
    }
  }

  return (
    <>
      <PageHeader title="My certificates" description="Your issued credentials wallet." />
      {loading || authLoading ? (
        <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState title="No certificates issued" description="Complete a subject to earn one." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {items.map((c) => (
            <div key={c.id} className="rounded-[var(--radius)] border bg-[var(--card)] p-4">
              <div className="mb-2 flex items-start justify-between gap-2">
                <h2 className="font-display text-lg">{c.template_name}</h2>
                <Badge>{c.status}</Badge>
              </div>
              <p className="text-sm text-[var(--muted-foreground)]">{c.class_title}</p>
              {c.subject_title ? (
                <p className="text-sm text-[var(--muted-foreground)]">{c.subject_title}</p>
              ) : null}
              <p className="mt-2 font-mono text-xs">{c.code}</p>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                Issued {new Date(c.issued_at).toLocaleDateString()}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button asChild size="sm" variant="outline">
                  <Link href={`/verify/${c.code}`}>Verify</Link>
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void copyLink(c.verify_url)}>
                  Copy link
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
