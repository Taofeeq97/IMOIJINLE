"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { api, type CertificateVerifyResult } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function VerifyPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const [code, setCode] = useState("");
  const [result, setResult] = useState<CertificateVerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void params.then(({ code: c }) => {
      setCode(c);
      api
        .verifyCertificate(c)
        .then((data) => {
          setResult(data);
          setError(null);
        })
        .catch((err: ApiError) => {
          setResult(null);
          setError(err.message || "Certificate not found");
        })
        .finally(() => setLoading(false));
    });
  }, [params]);

  useEffect(() => {
    if (!result?.json_ld) return;
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.text = JSON.stringify(result.json_ld);
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
  }, [result]);

  const statusTone =
    result?.status === "valid"
      ? "bg-[var(--success)]/15 text-[var(--success)]"
      : result?.status === "revoked"
        ? "bg-[var(--destructive)]/15 text-[var(--destructive)]"
        : "bg-[var(--muted)] text-[var(--muted-foreground)]";

  return (
    <>
      <PageHeader
        title="Certificate verification"
        description={code ? `Code: ${code}` : "Public credential check"}
      />
      {loading ? (
        <p className="text-sm text-[var(--muted-foreground)]">Checking…</p>
      ) : error || !result ? (
        <EmptyState title="Not found" description={error || "No certificate for this code."} />
      ) : (
        <div className="mx-auto max-w-lg space-y-4 rounded-[var(--radius)] border bg-[var(--card)] p-6">
          <div className="flex items-center justify-between gap-3">
            <p className="font-display text-2xl">{result.org_name}</p>
            <Badge className={statusTone}>{result.status}</Badge>
          </div>
          <div>
            <p className="text-sm text-[var(--muted-foreground)]">Issued to</p>
            <p className="font-display text-xl">{result.holder_name}</p>
          </div>
          <div className="grid gap-2 text-sm">
            {(result.cohort_title || result.program_title) ? (
              <p>
                <span className="text-[var(--muted-foreground)]">Cohort:</span>{" "}
                {result.cohort_title || result.program_title}
              </p>
            ) : null}
            {result.class_title ? (
              <p>
                <span className="text-[var(--muted-foreground)]">Class:</span> {result.class_title}
              </p>
            ) : null}
            {result.subject_title ? (
              <p>
                <span className="text-[var(--muted-foreground)]">Subject:</span> {result.subject_title}
              </p>
            ) : null}
            <p>
              <span className="text-[var(--muted-foreground)]">Issue date:</span> {result.issue_date}
            </p>
            <p className="font-mono text-xs">
              <span className="text-[var(--muted-foreground)]">Code:</span> {result.code}
            </p>
          </div>
          {result.status === "revoked" && result.revoked_reason ? (
            <p className="rounded-md bg-[var(--destructive)]/10 p-3 text-sm text-[var(--destructive)]">
              Revoked: {result.revoked_reason}
            </p>
          ) : null}
        </div>
      )}
    </>
  );
}
