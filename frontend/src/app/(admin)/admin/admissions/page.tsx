"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { AdaptiveDialog } from "@/components/adaptive/adaptive-dialog";
import { ResponsiveTable } from "@/components/adaptive/responsive-table";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api, type ApplicationItem, type ClassItem } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

function formatNaira(kobo: number | null) {
  if (kobo == null) return "—";
  return new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN" }).format(kobo / 100);
}

export default function AdminAdmissionsPage() {
  const [items, setItems] = useState<ApplicationItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<ApplicationItem | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [classIds, setClassIds] = useState<string[]>([]);
  const [admitting, setAdmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await api.listAdminApplications(statusFilter ? { status: statusFilter } : undefined);
      setItems(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [statusFilter]);

  async function openAdmit(app: ApplicationItem) {
    setSelected(app);
    setClassIds([]);
    try {
      const detail = await api.getAdminApplication(app.id);
      setSelected(detail);
      const cls = await api.listClasses(app.cohort);
      setClasses(cls.results.filter((c) => c.status === "published" || c.status === "draft"));
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  function toggleClass(id: string) {
    setClassIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function confirmAdmit() {
    if (!selected || classIds.length === 0) {
      toast.error("Select at least one class");
      return;
    }
    setAdmitting(true);
    try {
      await api.admitApplication(selected.id, { class_ids: classIds, fee_handling: "generate" });
      toast.success("Applicant admitted");
      setSelected(null);
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Admit failed");
    } finally {
      setAdmitting(false);
    }
  }

  const filters = useMemo(
    () => [
      { value: "", label: "All" },
      { value: "under_review", label: "Under review" },
      { value: "fee_paid", label: "Fee paid" },
      { value: "fee_pending", label: "Fee pending" },
      { value: "account_pending", label: "Account pending" },
      { value: "admitted", label: "Admitted" },
    ],
    [],
  );

  return (
    <>
      <PageHeader
        title="Admissions"
        description="Review applications and admit applicants into classes within a cohort."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((f) => (
          <Button
            key={f.value || "all"}
            size="sm"
            variant={statusFilter === f.value ? "default" : "outline"}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </Button>
        ))}
      </div>

      <ResponsiveTable
        title="Applications"
        description="Filter by status, then admit into one or more classes."
        loading={loading}
        emptyMessage="No applications"
        emptyDescription="When applicants apply to an open cohort, they appear here."
        columns={[
          {
            id: "applicant",
            header: "Applicant",
            priority: "high",
            cell: (app) => (
              <div>
                <div className="font-medium">{app.applicant_name}</div>
                <div className="text-xs text-[var(--muted-foreground)]">{app.applicant_email}</div>
              </div>
            ),
          },
          { id: "cohort", header: "Cohort", priority: "medium", cell: (app) => app.cohort_name },
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (app) => <Badge className="capitalize">{app.status.replaceAll("_", " ")}</Badge>,
          },
          {
            id: "fee",
            header: "Fee",
            priority: "low",
            cell: (app) =>
              app.fee_paid_at ? (
                <span className="text-[var(--primary)]">Paid {formatNaira(app.fee_amount_kobo)}</span>
              ) : (
                formatNaira(app.fee_amount_kobo)
              ),
          },
          {
            id: "actions",
            header: "",
            priority: "high",
            align: "right",
            cell: (app) => (
              <Button size="sm" onClick={() => void openAdmit(app)}>
                Admit
              </Button>
            ),
          },
        ]}
        data={items}
        getRowId={(app) => app.id}
      />

      <AdaptiveDialog
        open={Boolean(selected)}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
        title={selected ? `Admit ${selected.applicant_name}` : "Admit"}
        description={
          selected
            ? `${selected.applicant_email} · ${selected.status.replaceAll("_", " ")}${
                selected.fee_paid_at ? ` · Fee paid ${formatNaira(selected.fee_amount_kobo)}` : ""
              }`
            : undefined
        }
        footer={
          <>
            <Button variant="outline" onClick={() => setSelected(null)}>
              Cancel
            </Button>
            <Button onClick={() => void confirmAdmit()} disabled={admitting}>
              {admitting ? "Admitting…" : "Confirm admit"}
            </Button>
          </>
        }
      >
        <div>
          <Label className="mb-2 block">Select class(es)</Label>
          <ul className="space-y-2">
            {classes.map((c) => (
              <li key={c.id}>
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={classIds.includes(c.id)}
                    onChange={() => toggleClass(c.id)}
                  />
                  {c.name}{" "}
                  <span className="text-xs text-[var(--muted-foreground)]">({c.status})</span>
                </label>
              </li>
            ))}
            {classes.length === 0 ? (
              <p className="text-sm text-[var(--muted-foreground)]">No classes in this cohort.</p>
            ) : null}
          </ul>
        </div>
      </AdaptiveDialog>
    </>
  );
}
