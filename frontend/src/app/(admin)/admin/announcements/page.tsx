"use client";

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
import { api, getAccessToken } from "@/lib/api/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AnnouncementRow = {
  id: string;
  title: string;
  scope_type: string;
};

export default function AnnouncementsAdminPage() {
  const [rows, setRows] = useState<AnnouncementRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [editRow, setEditRow] = useState<AnnouncementRow | null>(null);
  const [deleteRow, setDeleteRow] = useState<AnnouncementRow | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/announcements`, {
        headers: { Authorization: `Bearer ${getAccessToken() || ""}` },
        credentials: "include",
      });
      const data = await r.json();
      setRows(Array.isArray(data) ? data : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load().catch((e: Error) => toast.error(e.message));
  }, []);

  function openCreate() {
    setTitle("");
    setBody("");
    setCreateOpen(true);
  }

  function openEdit(row: AnnouncementRow) {
    setEditRow(row);
    setTitle(row.title);
    setBody("");
  }

  async function publish() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      const r = await fetch(`${API_URL}/api/v1/announcements`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAccessToken() || ""}`,
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          scope_type: "global",
          title: title.trim(),
          body_json: { html: `<p>${body.trim() || title.trim()}</p>` },
        }),
      });
      if (!r.ok) throw new Error("Failed to publish");
      setCreateOpen(false);
      toast.success("Announcement published");
      await load();
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit() {
    if (!editRow || !title.trim()) return;
    setSaving(true);
    try {
      await api.updateAnnouncement(editRow.id, {
        title: title.trim(),
        body_json: body.trim() ? { html: `<p>${body.trim()}</p>` } : undefined,
      });
      setEditRow(null);
      toast.success("Announcement updated");
      await load();
    } catch (err) {
      toast.error((err as Error).message ?? "Update failed");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleteRow) return;
    setSaving(true);
    try {
      await api.deleteAnnouncement(deleteRow.id);
      setDeleteRow(null);
      toast.success("Announcement deleted");
      await load();
    } catch (err) {
      toast.error((err as Error).message ?? "Delete failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Announcements"
        description="Broadcast messages to learners globally, by cohort, or by class."
        actions={<Button onClick={openCreate}>New announcement</Button>}
      />

      <ResponsiveTable
        title="Published"
        description="Newest announcements appear first."
        loading={loading}
        emptyMessage="No announcements yet"
        emptyDescription="Create a global announcement to notify learners."
        columns={[
          { id: "title", header: "Title", priority: "high", cell: (r) => r.title },
          {
            id: "scope",
            header: "Scope",
            priority: "medium",
            cell: (r) => <Badge className="capitalize">{r.scope_type}</Badge>,
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
        title="New announcement"
        description="Publish a global notice. Cohort/class scoping can be added from later workflows."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void publish()} disabled={saving || !title.trim()}>
              {saving ? "Publishing…" : "Publish"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="ann-title">Title</Label>
          <Input
            id="ann-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Welcome to the new session"
            autoFocus
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ann-body">Description</Label>
          <Textarea
            id="ann-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Optional body text"
            rows={4}
          />
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(open) => {
          if (!open) setEditRow(null);
        }}
        title="Edit announcement"
        description="Update the announcement title and optional body."
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
          <Label htmlFor="edit-ann-title">Title</Label>
          <Input id="edit-ann-title" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
        </div>
        <div className="space-y-2">
          <Label htmlFor="edit-ann-body">Description</Label>
          <Textarea
            id="edit-ann-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Leave blank to keep the existing body"
            rows={4}
          />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(open) => {
          if (!open) setDeleteRow(null);
        }}
        title="Delete announcement?"
        description={deleteRow ? `Delete “${deleteRow.title}”?` : undefined}
        confirmLabel="Delete"
        tone="danger"
        loading={saving}
        onConfirm={() => void confirmDelete()}
      />
    </>
  );
}
