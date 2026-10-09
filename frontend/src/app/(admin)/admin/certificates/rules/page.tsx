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
import {
  api,
  type CertificateIssueRule,
  type CertificateTemplate,
  type ClassItem,
  type Subject,
} from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function CertificateRulesPage() {
  const [rules, setRules] = useState<CertificateIssueRule[]>([]);
  const [templates, setTemplates] = useState<CertificateTemplate[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editRow, setEditRow] = useState<CertificateIssueRule | null>(null);
  const [deleteRow, setDeleteRow] = useState<CertificateIssueRule | null>(null);
  const [name, setName] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [classId, setClassId] = useState("");
  const [autoIssue, setAutoIssue] = useState(true);
  const [minPct, setMinPct] = useState(100);
  const [feesCleared, setFeesCleared] = useState(false);
  const [enrollmentId, setEnrollmentId] = useState("");
  const [issueRuleId, setIssueRuleId] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [r, t, s, c] = await Promise.all([
        api.listCertificateRules(),
        api.listCertificateTemplates(),
        api.listSubjects(),
        api.listClasses(),
      ]);
      setRules(r);
      setTemplates(t.filter((x) => x.status === "published"));
      setSubjects(s.results);
      setClasses(c.results);
      if (!templateId && t.length) setTemplateId(t.find((x) => x.status === "published")?.id || "");
    } catch (err) {
      toast.error((err as ApiError).message ?? "Failed to load rules");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createRule() {
    if (!templateId) {
      toast.error("Select a published template");
      return;
    }
    if (!subjectId && !classId) {
      toast.error("Select a subject or class");
      return;
    }
    setSaving(true);
    try {
      await api.createCertificateRule({
        name: name.trim() || "Issue rule",
        template: templateId,
        subject: subjectId || null,
        class_ref: classId || null,
        auto_issue: autoIssue,
        criteria: {
          min_completion_pct: minPct,
          fees_cleared: feesCleared,
        },
      });
      toast.success("Rule created");
      setName("");
      setOpen(false);
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function manualIssue() {
    if (!enrollmentId.trim()) {
      toast.error("Enrollment ID required");
      return;
    }
    try {
      await api.issueCertificate({
        enrollment_id: enrollmentId.trim(),
        rule_id: issueRuleId || undefined,
        template_id: issueRuleId ? undefined : templateId || undefined,
        subject_id: subjectId || undefined,
        force: true,
      });
      toast.success("Certificate issued");
    } catch (err) {
      toast.error((err as ApiError).message ?? "Issue failed");
    }
  }

  function openEdit(row: CertificateIssueRule) {
    setEditRow(row);
    setName(row.name || "");
    setAutoIssue(row.auto_issue);
  }

  async function saveEdit() {
    if (!editRow) return;
    setSaving(true);
    try {
      await api.updateCertificateRule(editRow.id, {
        name: name.trim() || editRow.name,
        auto_issue: autoIssue,
      });
      setEditRow(null);
      toast.success("Rule updated");
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
      await api.deleteCertificateRule(deleteRow.id);
      setDeleteRow(null);
      toast.success("Rule deleted");
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
        title="Certificate issue rules"
        description="Bind published templates to a class or subject with eligibility criteria."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link href="/admin/certificates">Templates</Link>
            </Button>
            <Button onClick={() => setOpen(true)}>Create rule</Button>
          </div>
        }
      />

      <div className="mb-8">
        <ResponsiveTable
          title="Rules"
          description="Auto-issue when learners meet completion and fee criteria."
          loading={loading}
          emptyMessage="No rules yet"
          emptyDescription="Create a rule linked to a published template."
          columns={[
            { id: "name", header: "Name", priority: "high", cell: (r) => r.name || "—" },
            { id: "template", header: "Template", priority: "medium", cell: (r) => r.template_name },
            {
              id: "scope",
              header: "Scope",
              priority: "medium",
              cell: (r) =>
                r.subject_title
                  ? `Subject: ${r.subject_title}`
                  : r.class_name
                    ? `Class: ${r.class_name}`
                    : "—",
            },
            {
              id: "auto",
              header: "Auto",
              priority: "low",
              cell: (r) => <Badge>{r.auto_issue ? "yes" : "no"}</Badge>,
            },
            {
              id: "active",
              header: "Active",
              priority: "low",
              cell: (r) => (r.is_active ? "active" : "off"),
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
          data={rules}
          getRowId={(r) => r.id}
        />
      </div>

      <section className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)] p-4">
        <h2 className="font-display text-lg font-semibold">Manual issue</h2>
        <p className="mt-1 text-sm text-[var(--muted-foreground)]">
          Force-issue a certificate for a specific enrollment when needed.
        </p>
        <div className="mt-4 grid max-w-xl gap-3">
          <div className="space-y-2">
            <Label>Enrollment ID</Label>
            <Input value={enrollmentId} onChange={(e) => setEnrollmentId(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Rule (optional)</Label>
            <select
              className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
              value={issueRuleId}
              onChange={(e) => setIssueRuleId(e.target.value)}
            >
              <option value="">Use template / force</option>
              {rules.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name || r.template_name}
                </option>
              ))}
            </select>
          </div>
          <Button className="w-fit" onClick={() => void manualIssue()}>
            Issue certificate
          </Button>
        </div>
      </section>

      <AdaptiveDialog
        open={open}
        onOpenChange={setOpen}
        title="Create issue rule"
        description="Choose a published template and either a subject or class scope."
        className="w-[min(100%-2rem,36rem)]"
        footer={
          <>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void createRule()} disabled={saving}>
              {saving ? "Saving…" : "Create rule"}
            </Button>
          </>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2 sm:col-span-2">
            <Label>Title</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Subject completion" />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label>Template (published)</Label>
            <select
              className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
            >
              <option value="">Select…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Subject (optional)</Label>
            <select
              className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
              value={subjectId}
              onChange={(e) => setSubjectId(e.target.value)}
            >
              <option value="">—</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Class (optional)</Label>
            <select
              className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
              value={classId}
              onChange={(e) => setClassId(e.target.value)}
            >
              <option value="">—</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.cohort_name} · {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Min completion %</Label>
            <Input
              type="number"
              min={0}
              max={100}
              value={minPct}
              onChange={(e) => setMinPct(Number(e.target.value) || 0)}
            />
          </div>
          <div className="flex flex-col gap-2 pt-6">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={autoIssue} onChange={(e) => setAutoIssue(e.target.checked)} />
              Auto-issue on 100% progress
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={feesCleared}
                onChange={(e) => setFeesCleared(e.target.checked)}
              />
              Require fees cleared
            </label>
          </div>
        </div>
      </AdaptiveDialog>

      <AdaptiveDialog
        open={Boolean(editRow)}
        onOpenChange={(next) => {
          if (!next) setEditRow(null);
        }}
        title="Edit issue rule"
        description="Update the rule name and auto-issue setting."
        footer={
          <>
            <Button variant="outline" onClick={() => setEditRow(null)} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={() => void saveEdit()} disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <Label>Title</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={autoIssue} onChange={(e) => setAutoIssue(e.target.checked)} />
          Auto-issue on 100% progress
        </label>
      </AdaptiveDialog>

      <ConfirmDialog
        open={Boolean(deleteRow)}
        onOpenChange={(next) => {
          if (!next) setDeleteRow(null);
        }}
        title="Delete issue rule?"
        description={deleteRow ? `Delete “${deleteRow.name || deleteRow.template_name}”?` : undefined}
        confirmLabel="Delete"
        tone="danger"
        loading={saving}
        onConfirm={() => void confirmDelete()}
      />
    </>
  );
}
