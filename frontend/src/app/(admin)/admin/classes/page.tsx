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
import { api, type ClassItem } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function ClassesListPage() {
  const [rows, setRows] = useState<ClassItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editRow, setEditRow] = useState<ClassItem | null>(null);
  const [deleteRow, setDeleteRow] = useState<ClassItem | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await api.listClasses();
      setRows(data.results);
      setError(null);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function openEdit(row: ClassItem) {
    setEditRow(row);
    setName(row.name);
  }

  async function saveEdit() {
    if (!editRow || !name.trim()) return;
    setSaving(true);
    try {
      await api.updateClass(editRow.id, { name: name.trim() });
      setEditRow(null);
      toast.success("Class updated");
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
      await api.deleteClass(deleteRow.id);
      setDeleteRow(null);
      toast.success("Class deleted");
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
        title="Classes"
        description="Class tracks across all cohorts. Create new classes from a cohort workspace."
        actions={
          <Button asChild variant="outline">
            <Link href="/admin/cohorts">Open cohorts</Link>
          </Button>
        }
      />
      <ResponsiveTable
        title="All classes"
        description="Each class belongs to one cohort (academic session)."
        loading={loading}
        error={error}
        onRetry={() => void load()}
        emptyMessage="No classes yet"
        emptyDescription="Open a cohort and add Foundation, Advanced, or another class."
        columns={[
          {
            id: "name",
            header: "Class",
            priority: "high",
            cell: (r) => (
              <Link
                href={`/admin/classes/${r.id}`}
                className="font-medium text-[var(--primary)] underline-offset-2 hover:underline"
              >
                {r.name}
              </Link>
            ),
          },
          { id: "cohort", header: "Cohort", priority: "medium", cell: (r) => r.cohort_name },
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (r) => <Badge className="capitalize">{r.status}</Badge>,
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
        open={Boolean(editRow)}
        onOpenChange={(open) => {
          if (!open) setEditRow(null);
        }}
        title="Edit class"
        description="Rename this class track."
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
          <Label htmlFor="edit-class-name">Title</Label>
          <Input id="edit-class-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(open) => {
          if (!open) setDeleteRow(null);
        }}
        title="Delete class?"
        description={
          deleteRow
            ? `Delete “${deleteRow.name}”? Enrollments and attached subject links for this class may also be removed.`
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
