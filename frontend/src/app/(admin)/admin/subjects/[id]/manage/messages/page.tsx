"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function MessagesPage() {
  const params = useParams<{ id: string }>();
  const { refresh, markSaved } = useSubjectManage();
  const [welcome, setWelcome] = useState("");
  const [completion, setCompletion] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void api
      .getMessages(params.id)
      .then((m) => {
        setWelcome(m.welcome_message || "");
        setCompletion(m.completion_message || "");
      })
      .catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function save() {
    setSaving(true);
    try {
      await api.putMessages(params.id, {
        welcome_message: welcome,
        completion_message: completion,
      });
      markSaved();
      await refresh();
      toast.success("Messages saved");
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="font-display text-2xl">Subject messages</h2>
      <div className="space-y-1">
        <Label>Welcome message</Label>
        <textarea
          className="min-h-28 w-full rounded-md border border-[var(--border)] bg-transparent p-3 text-sm"
          value={welcome}
          onChange={(e) => setWelcome(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <Label>Completion message</Label>
        <textarea
          className="min-h-28 w-full rounded-md border border-[var(--border)] bg-transparent p-3 text-sm"
          value={completion}
          onChange={(e) => setCompletion(e.target.value)}
        />
      </div>
      <Button onClick={() => void save()} disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </Button>
    </div>
  );
}
