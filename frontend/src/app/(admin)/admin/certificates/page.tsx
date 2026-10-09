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
import { api, type CertificateTemplate, type IssuedCertificate } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function AdminCertificatesPage() {
  const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
  const [issued, setIssued] = useState<IssuedCertificate[]>([]);
  const [open, setOpen] = useState(false);
  const [editRow, setEditRow] = useState<CertificateTemplate | null>(null);
  const [deleteRow, setDeleteRow] = useState<CertificateTemplate | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [revokeReason, setRevokeReason] = useState<Record<string, string>>({});

  async function load() {
    setLoading(true);
    try {
      const [t, c] = await Promise.all([
        api.listCertificateTemplates(),
        api.listIssuedCertificates(),
      ]);
      setTemplates(t);
      setIssued(c);
    } catch (err) {
      toast.error((err as ApiError).message ?? "Failed to load certificates");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createTemplate() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const t = await api.createCertificateTemplate({ name: name.trim() });
      toast.success("Template created");
      setName("");
      setOpen(false);
      window.location.href = `/admin/certificates/${t.id}`;
    } catch (err) {
      toast.error((err as ApiError).message ?? "Create failed");
    } finally {
      setCreating(false);
    }
  }

  async function revoke(id: string) {
    try {
      await api.revokeCertificate(id, revokeReason[id] || "Revoked by admin");
      toast.success("Certificate revoked");
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Revoke failed");
    }
  }

  function openEdit(row: CertificateTemplate) {
    setEditRow(row);
    setName(row.name);
  }

  async function saveEdit() {
    if (!editRow || !name.trim()) return;
    setSaving(true);
    try {
      await api.updateCertificateTemplate(editRow.id, { name: name.trim() });
      setEditRow(null);
      toast.success("Template updated");
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
      await api.deleteCertificateTemplate(deleteRow.id);
      setDeleteRow(null);
      toast.success("Template deleted");
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
        title="Certificates"
        description="Design templates, publish versions, and manage issuance."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link href="/admin/certificates/rules">Issue rules</Link>
            </Button>
            <Button onClick={() => setOpen(true)}>Create template</Button>
          </div>
        }
      />

      <div className="mb-8">
        <ResponsiveTable
          title="Templates"
          description="Design layouts and publish a version before attaching issue rules."
          loading={loading}
          emptyMessage="No templates yet"
          emptyDescription="Create a template to get started."
          columns={[
            { id: "name", header: "Name", priority: "high", cell: (t) => t.name },
            {
              id: "status",
              header: "Status",
              priority: "medium",
              cell: (t) => <Badge className="capitalize">{t.status}</Badge>,
            },
            {
              id: "version",
              header: "Version",
              priority: "low",
              cell: (t) => `v${t.current_version_no ?? "—"}`,
            },
            {
              id: "actions",
              header: "Actions",
              priority: "high",
              align: "right",
              cell: (t) => (
                <TableRowActions
                  items={[{ label: "Design", href: `/admin/certificates/${t.id}` }]}
                  onEdit={() => openEdit(t)}
                  onDelete={() => setDeleteRow(t)}
                />
              ),
            },
          ]}
          data={templates}
          getRowId={(t) => t.id}
        />
      </div>

      <ResponsiveTable
        title="Issued"
        description="Certificates already granted to learners."
        loading={loading}
        emptyMessage="No certificates issued"
        emptyDescription="Issue from rules or after learners complete a subject/class."
        columns={[
          {
            id: "code",
            header: "Code",
            priority: "high",
            cell: (c) => <span className="font-mono text-xs">{c.code}</span>,
          },
          { id: "holder", header: "Holder", priority: "high", cell: (c) => c.holder_name },
          { id: "class", header: "Class", priority: "medium", cell: (c) => c.class_title },
          {
            id: "status",
            header: "Status",
            priority: "medium",
            cell: (c) => <Badge className="capitalize">{c.status}</Badge>,
          },
          {
            id: "actions",
            header: "Actions",
            priority: "high",
            align: "right",
            cell: (c) => (
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button asChild size="sm" variant="ghost">
                  <Link href={`/verify/${c.code}`} target="_blank">
                    Verify
                  </Link>
                </Button>
                {c.status === "issued" ? (
                  <>
                    <Input
                      className="h-8 w-32"
                      placeholder="Reason"
                      value={revokeReason[c.id] || ""}
                      onChange={(e) =>
                        setRevokeReason((prev) => ({ ...prev, [c.id]: e.target.value }))
                      }
                    />
                    <Button size="sm" variant="outline" onClick={() => void revoke(c.id)}>
                      Revoke
                    </Button>
                  </>
                ) : null}
              </div>
            ),
          },
        ]}
        data={issued}
        getRowId={(c) => c.id}
      />

      <AdaptiveDialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (next) setName("");
        }}
        title="Create certificate template"
        description="Start a design draft. Publish a version before using it in issue rules."
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={creating}>
              Cancel
            </Button>
            <Button onClick={() => void createTemplate()} disabled={creating || !name.trim()}>
              {creating ? "Creating…" : "Create template"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label htmlFor="tpl-name">Title</Label>
          <Input
            id="tpl-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Classic completion certificate"
            autoFocus
          />
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(next) => {
          if (!next) setEditRow(null);
        }}
        title="Edit template"
        description="Rename this certificate template."
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
          <Label htmlFor="edit-tpl-name">Title</Label>
          <Input id="edit-tpl-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(next) => {
          if (!next) setDeleteRow(null);
        }}
        title="Delete template?"
        description={
          deleteRow
            ? `Delete “${deleteRow.name}”? Issue rules using this template may break.`
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
