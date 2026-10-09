"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type GradingQueueItem } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function AdminGradingPage() {
  const [items, setItems] = useState<GradingQueueItem[]>([]);
  const [selected, setSelected] = useState<GradingQueueItem | null>(null);
  const [scores, setScores] = useState<Record<string, number>>({});
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const data = await api.gradingQueue();
    setItems(data.results);
  }

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, []);

  function openItem(item: GradingQueueItem) {
    setSelected(item);
    const initial: Record<string, number> = {};
    for (const c of item.rubric?.criteria || []) {
      initial[c.id] = c.max_points ?? 0;
    }
    setScores(initial);
    setFeedback("");
  }

  const previewTotal = useMemo(
    () => Object.values(scores).reduce((a, b) => a + (Number(b) || 0), 0),
    [scores],
  );

  async function saveGrade(release: boolean) {
    if (!selected) return;
    setBusy(true);
    try {
      const rubric_scores: Record<string, { points: number }> = {};
      for (const [id, points] of Object.entries(scores)) {
        rubric_scores[id] = { points: Number(points) || 0 };
      }
      const graded = await api.gradeSubmission(selected.submission_id, {
        rubric_scores,
        feedback_json: { comment: feedback },
        raw_score: selected.rubric ? undefined : previewTotal,
      });
      if (release) {
        await api.releaseGrades([selected.submission_id]);
        toast.success(`Graded & released · ${graded.final_score}`);
      } else {
        toast.success(`Saved grade · ${graded.final_score}`);
      }
      setSelected(null);
      await load();
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Grading"
        description="Speed-grade assignment submissions and release scores to students."
      />

      {items.length === 0 ? (
        <EmptyState
          title="Queue is empty"
          description="When students submit assignments, they appear here for tutors."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.submission_id}>
                <button
                  type="button"
                  onClick={() => openItem(item)}
                  className={`w-full rounded-lg border px-4 py-3 text-left text-sm ${
                    selected?.submission_id === item.submission_id
                      ? "border-[var(--primary)] bg-[var(--secondary)]"
                      : "border-[var(--border)] hover:bg-[var(--muted)]"
                  }`}
                >
                  <p className="font-medium">{item.assignment_title}</p>
                  <p className="text-[var(--muted-foreground)]">
                    {item.student_name} · {item.student_email}
                  </p>
                </button>
              </li>
            ))}
          </ul>

          {selected ? (
            <div className="space-y-4 rounded-lg border border-[var(--border)] p-4">
              <div>
                <h2 className="font-display text-lg">{selected.assignment_title}</h2>
                <p className="text-sm text-[var(--muted-foreground)]">{selected.student_name}</p>
              </div>
              {selected.text ? (
                <div className="rounded-md bg-[var(--muted)]/40 p-3 text-sm whitespace-pre-wrap">
                  {selected.text}
                </div>
              ) : null}
              {selected.link ? (
                <a className="text-sm underline" href={selected.link} target="_blank" rel="noreferrer">
                  Open submission link
                </a>
              ) : null}

              {(selected.rubric?.criteria || []).map((c) => (
                <div key={c.id} className="space-y-1">
                  <Label htmlFor={`score-${c.id}`}>
                    {c.title}
                    {c.max_points != null ? ` (max ${c.max_points})` : ""}
                  </Label>
                  <Input
                    id={`score-${c.id}`}
                    type="number"
                    value={scores[c.id] ?? 0}
                    onChange={(e) =>
                      setScores((prev) => ({ ...prev, [c.id]: Number(e.target.value) }))
                    }
                  />
                </div>
              ))}

              {!selected.rubric ? (
                <div className="space-y-1">
                  <Label htmlFor="raw">Score (max {selected.points})</Label>
                  <Input
                    id="raw"
                    type="number"
                    value={previewTotal}
                    onChange={(e) => setScores({ raw: Number(e.target.value) })}
                  />
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">Total preview: {previewTotal}</p>
              )}

              <div className="space-y-1">
                <Label htmlFor="fb">Feedback</Label>
                <textarea
                  id="fb"
                  className="min-h-24 w-full rounded-md border border-[var(--border)] bg-transparent p-2 text-sm"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button disabled={busy} onClick={() => void saveGrade(false)}>
                  Save grade
                </Button>
                <Button disabled={busy} onClick={() => void saveGrade(true)}>
                  Save & release
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Select a submission to grade.</p>
          )}
        </div>
      )}
    </>
  );
}
