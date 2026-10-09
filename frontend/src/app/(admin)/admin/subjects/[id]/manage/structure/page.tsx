"use client";

import { useSubjectManage } from "@/app/(admin)/admin/subjects/[id]/manage/layout";

export default function StructurePage() {
  const { checklist } = useSubjectManage();
  const stats = checklist?.stats;
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="font-display text-2xl">Subject structure</h2>
      <p className="text-sm text-[var(--muted-foreground)]">
        Quality bar warns but does not block publish. Build curriculum under Curriculum.
      </p>
      <ul className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 text-sm">
        <li>Topics: {stats?.topics ?? 0} (min 1)</li>
        <li>Subtopics: {stats?.subtopics ?? 0} (min 1)</li>
        <li>With content: {stats?.with_content ?? 0}</li>
        <li>Video minutes: {stats?.video_minutes ?? 0}</li>
      </ul>
    </div>
  );
}
