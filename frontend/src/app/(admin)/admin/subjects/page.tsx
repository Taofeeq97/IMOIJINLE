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
import { api, type Subject } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function SubjectsLibraryPage() {
  const [rows, setRows] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editRow, setEditRow] = useState<Subject | null>(null);
  const [deleteRow, setDeleteRow] = useState<Subject | null>(null);
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await api.listSubjects();
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

  function openCreate() {
    setTitle("");
    setSubtitle("");
    setCreateOpen(true);
  }

  function openEdit(row: Subject) {
    setEditRow(row);
    setTitle(row.title);
    setSubtitle(row.subtitle || "");
  }

  async function create() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const s = await api.createSubject({
        title: title.trim(),
        subtitle: subtitle.trim() || undefined,
        level: "beginner",
      });
      setCreateOpen(false);
      toast.success("Subject created");
      window.location.href = `/admin/subjects/${s.id}`;
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit() {
    if (!editRow || !title.trim()) return;
    setSaving(true);
    try {
      await api.updateSubject(editRow.id, {
        title: title.trim(),
        subtitle: subtitle.trim(),
      });
      setEditRow(null);
      toast.success("Subject updated");
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
      await api.deleteSubject(deleteRow.id);
      setDeleteRow(null);
      toast.success("Subject deleted");
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
        title="Subject Library"
        description="Reusable subjects (courses) you can attach to any class."
        actions={<Button onClick={openCreate}>Create subject</Button>}
      />

      <ResponsiveTable
        title="Subjects"
        description="Draft and published subjects available for class attachment."
        loading={loading}
        error={error}
        onRetry={() => void load()}
        emptyMessage="No subjects yet"
        emptyDescription="Create a subject, then build its curriculum."
        columns={[
          {
            id: "title",
            header: "Subject",
            priority: "high",
            cell: (r) => (
              <div>
                <Link
                  href={`/admin/subjects/${r.id}`}
                  className="font-medium text-[var(--primary)] underline-offset-2 hover:underline"
                >
                  {r.title}
                </Link>
                {r.subtitle ? (
                  <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{r.subtitle}</p>
                ) : null}
              </div>
            ),
          },
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (r) => <Badge className="capitalize">{r.status.replaceAll("_", " ")}</Badge>,
          },
          { id: "topics", header: "Topics", priority: "low", cell: (r) => r.topic_count },
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
        title="Create subject"
        description="Subjects are reusable courses. Attach them to classes after authoring."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void create()} disabled={saving || !title.trim()}>
              {saving ? "Creating…" : "Create subject"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="subject-title">Title</Label>
          <Input
            id="subject-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Introduction to Spirit Science"
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="subject-subtitle">Description</Label>
          <Input
            id="subject-subtitle"
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
            placeholder="Short subtitle shown on the landing page"
          />
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(open) => {
          if (!open) setEditRow(null);
        }}
        title="Edit subject"
        description="Update the subject title and subtitle."
        footer={
          <>
            <Button variant="outline" onClick={() => setEditRow(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void saveEdit()} disabled={saving || !title.trim()}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="edit-subject-title">Title</Label>
          <Input id="edit-subject-title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-subject-subtitle">Description</Label>
          <Input
            id="edit-subject-subtitle"
            value={subtitle}
            onChange={(e) => setSubtitle(e.target.value)}
          />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(open) => {
          if (!open) setDeleteRow(null);
        }}
        title="Delete subject?"
        description={
          deleteRow
            ? `Delete “${deleteRow.title}”? Curriculum and class attachments for this subject may also be removed.`
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
