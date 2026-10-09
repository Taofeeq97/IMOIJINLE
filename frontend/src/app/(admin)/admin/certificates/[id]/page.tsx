"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type CertificateTemplate } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function CertificateTemplateEditorPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [template, setTemplate] = useState<CertificateTemplate | null>(null);
  const [designText, setDesignText] = useState("");
  const [previewHtml, setPreviewHtml] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [publishing, setPublishing] = useState(false);

  async function load() {
    try {
      const t = await api.getCertificateTemplate(id);
      setTemplate(t);
      setDesignText(JSON.stringify(t.current_design ?? {}, null, 2));
    } catch (err) {
      toast.error((err as ApiError).message ?? "Failed to load template");
    }
  }

  useEffect(() => {
    void load();
  }, [id]);

  const parsedDesign = useMemo(() => {
    try {
      return JSON.parse(designText) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [designText]);

  const elements = useMemo(() => {
    const design = parsedDesign;
    if (!design || !Array.isArray(design.elements)) return [];
    return design.elements as { id?: string; type?: string; text?: string }[];
  }, [parsedDesign]);

  async function save() {
    if (!parsedDesign) {
      toast.error("Design JSON is invalid");
      return;
    }
    setSaving(true);
    try {
      const t = await api.updateCertificateTemplate(id, { design: parsedDesign });
      setTemplate(t);
      toast.success("Design saved");
    } catch (err) {
      toast.error((err as ApiError).message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function preview() {
    if (!parsedDesign) {
      toast.error("Design JSON is invalid");
      return;
    }
    setPreviewing(true);
    try {
      const result = await api.previewCertificateTemplate(id, {
        design: parsedDesign,
        data_source: "sample",
      });
      setPreviewHtml(result.html);
      setWarnings(result.warnings || []);
      toast.success("Preview rendered");
      await load();
    } catch (err) {
      toast.error((err as ApiError).message ?? "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function publish() {
    setPublishing(true);
    try {
      const result = await api.publishCertificateTemplate(id);
      setTemplate(result.template);
      toast.success(`Published v${result.version.version_no}`);
    } catch (err) {
      toast.error((err as ApiError).message ?? "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <>
      <PageHeader
        title={template?.name || "Certificate template"}
        description="Edit design JSON, preview with sample data, then publish."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <Link href="/admin/certificates">Back</Link>
            </Button>
            {template ? <Badge>{template.status}</Badge> : null}
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Button onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save design"}
        </Button>
        <Button variant="secondary" onClick={() => void preview()} disabled={previewing}>
          {previewing ? "Rendering…" : "Preview (sample)"}
        </Button>
        <Button variant="outline" onClick={() => void publish()} disabled={publishing}>
          {publishing ? "Publishing…" : "Publish"}
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <Label htmlFor="design-json">Design JSON (schema_version 1)</Label>
          <Textarea
            id="design-json"
            className="min-h-[420px] font-mono text-xs"
            value={designText}
            onChange={(e) => setDesignText(e.target.value)}
          />
          {!parsedDesign ? (
            <p className="text-sm text-[var(--destructive)]">Invalid JSON</p>
          ) : null}
          <div>
            <p className="mb-2 text-sm font-medium">Elements</p>
            <ul className="space-y-1 text-sm text-[var(--muted-foreground)]">
              {elements.map((el, idx) => (
                <li key={el.id || idx}>
                  <span className="font-mono text-xs">{el.type || "unknown"}</span>
                  {el.text ? ` — ${el.text.slice(0, 60)}` : ""}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="space-y-3">
          <Label>Server preview</Label>
          {warnings.length > 0 ? (
            <ul className="rounded-md border border-[var(--warning)]/40 bg-[var(--warning)]/10 p-3 text-sm">
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          <div className="overflow-auto rounded-[var(--radius)] border bg-[var(--muted)]/20 p-2">
            {previewHtml ? (
              <iframe
                title="Certificate preview"
                srcDoc={previewHtml}
                className="h-[520px] w-full rounded bg-white"
              />
            ) : (
              <p className="p-6 text-sm text-[var(--muted-foreground)]">
                Click Preview to render sample student data server-side.
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
