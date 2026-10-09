"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

function ListEditor({
  label,
  hint,
  values,
  onChange,
  maxLen = 160,
}: {
  label: string;
  hint: string;
  values: string[];
  onChange: (next: string[]) => void;
  maxLen?: number;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <p className="text-xs text-[var(--muted-foreground)]">{hint}</p>
      {values.map((v, i) => (
        <div key={i} className="flex gap-2">
          <Input
            value={v}
            maxLength={maxLen}
            onChange={(e) => {
              const next = [...values];
              next[i] = e.target.value;
              onChange(next);
            }}
          />
          <Button type="button" variant="outline" onClick={() => onChange(values.filter((_, j) => j !== i))}>
            Remove
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" onClick={() => onChange([...values, ""])}>
        Add
      </Button>
    </div>
  );
}

export default function IntendedLearnersPage() {
  const params = useParams<{ id: string }>();
  const { refresh, markSaved } = useSubjectManage();
  const [learn, setLearn] = useState<string[]>([]);
  const [requirements, setRequirements] = useState<string[]>([]);
  const [audience, setAudience] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void api
      .getIntendedLearners(params.id)
      .then((data) => {
        setLearn(data.learn?.length ? data.learn : ["", "", "", ""]);
        setRequirements(data.requirements?.length ? data.requirements : [""]);
        setAudience(data.audience?.length ? data.audience : [""]);
      })
      .catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function save() {
    setSaving(true);
    try {
      await api.putIntendedLearners(params.id, {
        learn: learn.map((s) => s.trim()).filter(Boolean),
        requirements: requirements.map((s) => s.trim()).filter(Boolean),
        audience: audience.map((s) => s.trim()).filter(Boolean),
      });
      markSaved();
      await refresh();
      toast.success("Saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="font-display text-2xl">Intended learners</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          These lists appear on the subject landing page. Aim for at least 4 learning objectives.
        </p>
      </div>
      <ListEditor
        label="What will students learn"
        hint="Min 4 · max 160 characters each"
        values={learn}
        onChange={setLearn}
      />
      <ListEditor
        label="Requirements / prerequisites"
        hint="What students need before starting"
        values={requirements}
        onChange={setRequirements}
        maxLen={200}
      />
      <ListEditor
        label="Who this subject is for"
        hint="Audience descriptions"
        values={audience}
        onChange={setAudience}
        maxLen={200}
      />
      <Button onClick={() => void save()} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
