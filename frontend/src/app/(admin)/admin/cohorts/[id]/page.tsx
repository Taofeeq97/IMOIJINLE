"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
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
import { Textarea } from "@/components/ui/textarea";
import { api, type ClassItem, type Cohort } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function CohortDetailPage() {
  const params = useParams<{ id: string }>();
  const [cohort, setCohort] = useState<Cohort | null>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editRow, setEditRow] = useState<ClassItem | null>(null);
  const [deleteRow, setDeleteRow] = useState<ClassItem | null>(null);
  const [className, setClassName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    const [c, cls] = await Promise.all([
      api.getCohort(params.id),
      api.listClasses(params.id),
    ]);
    setCohort(c);
    setClasses(cls.results);
  }

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function openApps() {
    try {
      const c = await api.openApplications(params.id);
      setCohort(c);
      toast.success("Applications opened");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function closeApps() {
    try {
      const c = await api.closeApplications(params.id);
      setCohort(c);
      toast.success("Applications closed");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  function openEdit(row: ClassItem) {
    setEditRow(row);
    setClassName(row.name);
    setDescription("");
  }

  async function addClass() {
    if (!className.trim()) return;
    setSaving(true);
    try {
      const created = await api.createClass({ name: className.trim(), cohort: params.id });
      setClassName("");
      setDescription("");
      setOpen(false);
      toast.success("Class created");
      await load();
      window.location.href = `/admin/classes/${created.id}`;
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit() {
    if (!editRow || !className.trim()) return;
    setSaving(true);
    try {
      await api.updateClass(editRow.id, { name: className.trim() });
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

  if (!cohort) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;

  return (
    <>
      <PageHeader
        title={cohort.name}
        description={`Academic session · apply at ${cohort.public_apply_path}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void openApps()}>
              Open applications
            </Button>
            <Button variant="secondary" onClick={() => void closeApps()}>
              Close applications
            </Button>
            <Button onClick={() => setOpen(true)}>Add class</Button>
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap gap-2">
        <Badge className="capitalize">{cohort.status.replaceAll("_", " ")}</Badge>
        <Badge className="bg-[var(--muted)]">Capacity {cohort.capacity}</Badge>
      </div>

      <ResponsiveTable
        title="Classes"
        description="Students are admitted into a class within this cohort."
        emptyMessage="No classes yet"
        emptyDescription="Add Foundation, Advanced, or other class tracks."
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
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (r) => <Badge className="capitalize">{r.status}</Badge>,
          },
          { id: "capacity", header: "Capacity", priority: "low", cell: (r) => r.capacity },
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
        data={classes}
        getRowId={(r) => r.id}
      />

      <AdaptiveDialog
        open={open}
        onOpenChange={setOpen}
        title="Add class"
        description="Create a class track inside this academic session."
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void addClass()} disabled={saving || !className.trim()}>
              {saving ? "Creating…" : "Create class"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="class-name">Title</Label>
          <Input
            id="class-name"
            value={className}
            onChange={(e) => setClassName(e.target.value)}
            placeholder="Foundation Class"
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="class-desc">Description</Label>
          <Textarea
            id="class-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional notes for staff (not required to create)"
            rows={3}
          />
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(o) => {
          if (!o) setEditRow(null);
        }}
        title="Edit class"
        description="Rename this class track."
        footer={
          <>
            <Button variant="outline" onClick={() => setEditRow(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void saveEdit()} disabled={saving || !className.trim()}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="edit-class-name">Title</Label>
          <Input
            id="edit-class-name"
            value={className}
            onChange={(e) => setClassName(e.target.value)}
            autoFocus
          />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(o) => {
          if (!o) setDeleteRow(null);
        }}
        title="Delete class?"
        description={
          deleteRow
            ? `Delete “${deleteRow.name}” from this cohort?`
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
