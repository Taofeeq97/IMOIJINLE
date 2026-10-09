"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { AdaptiveDialog } from "@/components/adaptive/adaptive-dialog";
import { ResponsiveTable } from "@/components/adaptive/responsive-table";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageHeader } from "@/components/shared/page-header";
import { TableRowActions } from "@/components/shared/table-row-actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Cohort } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function CohortsAdminPage() {
  const [rows, setRows] = useState<Cohort[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editRow, setEditRow] = useState<Cohort | null>(null);
  const [deleteRow, setDeleteRow] = useState<Cohort | null>(null);
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("50");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listCohorts();
      setRows(data.results);
    } catch (err) {
      setError((err as ApiError).message ?? "Failed to load cohorts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function openCreate() {
    setName("");
    setCapacity("50");
    setCreateOpen(true);
  }

  function openEdit(row: Cohort) {
    setEditRow(row);
    setName(row.name);
    setCapacity(String(row.capacity ?? 50));
  }

  async function createCohort() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const created = await api.createCohort({
        name: name.trim(),
        capacity: Number(capacity) || 50,
      });
      setCreateOpen(false);
      toast.success("Cohort created");
      await load();
      window.location.href = `/admin/cohorts/${created.id}`;
    } catch (err) {
      toast.error((err as ApiError).message ?? "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit() {
    if (!editRow || !name.trim()) return;
    setSaving(true);
    try {
      await api.updateCohort(editRow.id, {
        name: name.trim(),
        capacity: Number(capacity) || 50,
      });
      setEditRow(null);
      toast.success("Cohort updated");
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Update failed");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleteRow) return;
    setSaving(true);
    try {
      await api.deleteCohort(deleteRow.id);
      setDeleteRow(null);
      toast.success("Cohort deleted");
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Delete failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Cohorts"
        description="Academic sessions. Create a cohort, open applications, then add classes."
        actions={<Button onClick={openCreate}>Create cohort</Button>}
      />

      <ResponsiveTable
        title="All cohorts"
        description="Each cohort is an academic session with its own classes and admissions."
        loading={loading}
        error={error}
        onRetry={() => void load()}
        emptyMessage="No cohorts yet"
        emptyDescription="Create a cohort to open applications and attach classes."
        columns={[
          {
            id: "name",
            header: "Cohort",
            priority: "high",
            cell: (r) => (
              <Link
                className="font-medium text-[var(--primary)] underline-offset-2 hover:underline"
                href={`/admin/cohorts/${r.id}`}
              >
                {r.name}
              </Link>
            ),
          },
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (r) => <Badge className="capitalize">{r.status.replaceAll("_", " ")}</Badge>,
          },
          { id: "capacity", header: "Capacity", priority: "low", cell: (r) => r.capacity },
          {
            id: "apply",
            header: "Apply path",
            priority: "low",
            cell: (r) => (
              <span className="font-mono text-xs text-[var(--muted-foreground)]">{r.public_apply_path}</span>
            ),
          },
          {
            id: "actions",
            header: "Actions",
            priority: "high",
            align: "right",
            cell: (r) => (
              <TableRowActions onEdit={() => openEdit(r)} onDelete={() => setDeleteRow(r)} />
            ),
          },
        ]}
        data={rows}
        getRowId={(r) => r.id}
      />

      <AdaptiveDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Create cohort"
        description="A cohort is an academic session (for example 2026/2027)."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void createCohort()} disabled={saving || !name.trim()}>
              {saving ? "Creating…" : "Create cohort"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="cohort-name">Title</Label>
          <Input
            id="cohort-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="2026/2027 Academic Session"
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="cohort-capacity">Capacity</Label>
          <Input
            id="cohort-capacity"
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(open) => {
          if (!open) setEditRow(null);
        }}
        title="Edit cohort"
        description="Update the academic session title or capacity."
        footer={
          <>
            <Button variant="outline" onClick={() => setEditRow(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void saveEdit()} disabled={saving || !name.trim()}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="edit-cohort-name">Title</Label>
          <Input id="edit-cohort-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-cohort-capacity">Capacity</Label>
          <Input
            id="edit-cohort-capacity"
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(open) => {
          if (!open) setDeleteRow(null);
        }}
        title="Delete cohort?"
        description={
          deleteRow
            ? `Delete “${deleteRow.name}”? Classes and related records under this cohort may also be removed.`
            : undefined
        }
        confirmLabel="Delete"
        tone="danger"
        loading={saving}
        onConfirm={() => void confirmDelete()}
      />
    </>
  );
}
