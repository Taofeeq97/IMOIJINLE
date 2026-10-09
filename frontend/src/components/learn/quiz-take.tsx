"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  api,
  type QuizAttemptReview,
  type QuizDetail,
} from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

type Props = {
  subtopicId: string;
  onComplete?: () => void;
};

export function QuizTake({ subtopicId, onComplete }: Props) {
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, Record<string, unknown>>>({});
  const [review, setReview] = useState<QuizAttemptReview | null>(null);
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setQuiz(null);
    setAttemptId(null);
    setAnswers({});
    setReview(null);
    setMissing(false);
    void api
      .getSubtopicQuiz(subtopicId)
      .then(setQuiz)
      .catch((err: ApiError) => {
        if (err.code === "not_found") setMissing(true);
        else toast.error(err.message);
      });
  }, [subtopicId]);

  async function start() {
    if (!quiz) return;
    setBusy(true);
    try {
      const attempt = await api.startQuizAttempt(quiz.id);
      setAttemptId(attempt.id);
      setReview(null);
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!quiz || !attemptId) return;
    setBusy(true);
    try {
      const responses = quiz.questions.map((q) => ({
        question_id: q.id,
        answer: answers[q.id] || {},
      }));
      await api.saveAttemptResponses(attemptId, responses);
      const submitted = await api.submitQuizAttempt(attemptId);
      toast.success(
        submitted.released
          ? `Submitted · score ${submitted.score}/${submitted.max_score}`
          : "Submitted",
      );
      const rev = await api.reviewQuizAttempt(attemptId);
      setReview(rev);
      onComplete?.();
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  if (missing) {
    return (
      <div className="rounded-lg bg-[var(--card)] p-6 text-sm text-[var(--muted-foreground)]">
        No quiz configured for this subtopic yet.
      </div>
    );
  }

  if (!quiz) {
    return <p className="text-sm text-[var(--muted-foreground)]">Loading quiz…</p>;
  }

  if (review?.released) {
    return (
      <div className="space-y-4 rounded-lg bg-[var(--card)] p-6 text-[var(--foreground)]">
        <div>
          <h2 className="font-display text-xl">{quiz.title}</h2>
          <p className="mt-1 text-sm">
            Score: {review.score}/{review.max_score}
          </p>
        </div>
        <ul className="space-y-3">
          {(review.responses || []).map((r) => (
            <li key={r.question_id} className="rounded border border-[var(--border)] p-3 text-sm">
              <p className="font-medium">{r.prompt}</p>
              <p className="mt-1 text-[var(--muted-foreground)]">
                {r.is_correct ? "Correct" : "Incorrect"} · {r.score}/{r.points}
              </p>
            </li>
          ))}
        </ul>
        <Button variant="outline" onClick={() => { setReview(null); setAttemptId(null); }}>
          Retake / close
        </Button>
      </div>
    );
  }

  if (!attemptId) {
    return (
      <div className="space-y-4 rounded-lg bg-[var(--card)] p-6 text-[var(--foreground)]">
        <h2 className="font-display text-xl">{quiz.title}</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          {quiz.questions.length} questions · {quiz.points_total} points
        </p>
        <Button onClick={() => void start()} disabled={busy}>
          Start quiz
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-lg bg-[var(--card)] p-6 text-[var(--foreground)]">
      <h2 className="font-display text-xl">{quiz.title}</h2>
      <ul className="space-y-5">
        {quiz.questions.map((q, idx) => (
          <li key={q.id} className="space-y-2">
            <p className="font-medium">
              {idx + 1}. {q.prompt}{" "}
              <span className="text-xs text-[var(--muted-foreground)]">({q.points} pts)</span>
            </p>
            {q.question_type === "mcq" || q.question_type === "true_false" ? (
              <div className="space-y-1">
                {(q.choices || []).map((c) => (
                  <label key={c.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name={q.id}
                      checked={(answers[q.id]?.choice_id ?? answers[q.id]?.value) === c.id ||
                        (q.question_type === "true_false" &&
                          answers[q.id]?.value === (c.id === "t" || c.text.toLowerCase() === "true"))}
                      onChange={() => {
                        if (q.question_type === "true_false") {
                          const val = c.id === "t" || c.text.toLowerCase() === "true";
                          setAnswers((prev) => ({ ...prev, [q.id]: { value: val } }));
                        } else {
                          setAnswers((prev) => ({ ...prev, [q.id]: { choice_id: c.id } }));
                        }
                      }}
                    />
                    {c.text}
                  </label>
                ))}
              </div>
            ) : (
              <Input
                placeholder="Your answer"
                value={String(answers[q.id]?.text ?? "")}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [q.id]: { text: e.target.value } }))
                }
              />
            )}
          </li>
        ))}
      </ul>
      <Button onClick={() => void submit()} disabled={busy}>
        Submit answers
      </Button>
    </div>
  );
}
