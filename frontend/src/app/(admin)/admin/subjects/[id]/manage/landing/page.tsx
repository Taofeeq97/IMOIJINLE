"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { RichTextEditor } from "@/components/editor/rich-text-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function LandingPageEditor() {
  const params = useParams<{ id: string }>();
  const { subject, refresh, markSaved } = useSubjectManage();
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [html, setHtml] = useState("<p></p>");
  const [language, setLanguage] = useState("en");
  const [level, setLevel] = useState("all");
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [promo, setPromo] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!subject) return;
    setTitle(subject.title.slice(0, 60));
    setSubtitle((subject.subtitle || "").slice(0, 120));
    setHtml(String(subject.description_json?.html ?? "<p></p>"));
    setLanguage(subject.language || "en");
    setLevel(subject.level || "all");
    setCategory(subject.category || "");
    setSubcategory(subject.subcategory || "");
    setPromo(subject.promo_video || "");
  }, [subject]);

  async function save() {
    setSaving(true);
    try {
      await api.putLanding(params.id, {
        title,
        subtitle,
        description_json: { html },
        language,
        level,
        category,
        subcategory,
        promo_video: promo,
      });
      markSaved();
      await refresh();
      toast.success("Landing page saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h2 className="font-display text-2xl">Subject landing page</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Title ≤ 60 · subtitle ≤ 120 · description supports rich text.
        </p>
      </div>
      <div className="space-y-1">
        <Label>Title ({title.length}/60)</Label>
        <Input value={title} maxLength={60} onChange={(e) => setTitle(e.target.value)} />
      </div>
      <div className="space-y-1">
        <Label>Subtitle ({subtitle.length}/120)</Label>
        <Input value={subtitle} maxLength={120} onChange={(e) => setSubtitle(e.target.value)} />
      </div>
      <div className="space-y-1">
        <Label>Description</Label>
        <RichTextEditor valueHtml={html} onChange={setHtml} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <Label>Language</Label>
          <Input value={language} onChange={(e) => setLanguage(e.target.value)} />
        </div>
        <div className="space-y-1">
          <Label>Level</Label>
          <select
            className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
            <option value="all">All levels</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label>Category</Label>
          <Input value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
        <div className="space-y-1">
          <Label>Subcategory</Label>
          <Input value={subcategory} onChange={(e) => setSubcategory(e.target.value)} />
        </div>
      </div>
      <div className="space-y-1">
        <Label>Promotional video URL</Label>
        <Input value={promo} onChange={(e) => setPromo(e.target.value)} placeholder="https://…" />
      </div>
      <Button onClick={() => void save()} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
