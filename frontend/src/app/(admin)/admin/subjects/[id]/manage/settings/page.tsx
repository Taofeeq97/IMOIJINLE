"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function SubjectSettingsPage() {
  const params = useParams<{ id: string }>();
  const { refresh, markSaved } = useSubjectManage();
  const [qa, setQa] = useState(true);
  const [reviews, setReviews] = useState("off");
  const [sequential, setSequential] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void api
      .getSubjectSettings(params.id)
      .then((s) => {
        setQa(s.qa_enabled !== false);
        setReviews(String(s.reviews ?? "off"));
        setSequential(Boolean(s.sequential));
      })
      .catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function save() {
    setSaving(true);
    try {
      await api.putSubjectSettings(params.id, {
        qa_enabled: qa,
        reviews,
        sequential,
        study_time_defaults: { min_time_s: 60 },
      });
      markSaved();
      await refresh();
      toast.success("Settings saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <h2 className="font-display text-2xl">Settings</h2>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={qa} onChange={(e) => setQa(e.target.checked)} />
        Q&A enabled
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={sequential}
          onChange={(e) => setSequential(e.target.checked)}
        />
        Sequential drip (unlock next after complete)
      </label>
      <div className="space-y-1 text-sm">
        <p>Reviews</p>
        <select
          className="flex h-10 w-full rounded-md border border-[var(--border)] bg-transparent px-3 text-sm"
          value={reviews}
          onChange={(e) => setReviews(e.target.value)}
        >
          <option value="off">Off</option>
          <option value="private">Private</option>
          <option value="cohort">Public to cohort</option>
        </select>
      </div>
      <Button onClick={() => void save()} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
