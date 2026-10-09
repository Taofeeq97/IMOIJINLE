"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { QuizTake } from "@/components/learn/quiz-take";
import { LearningShell } from "@/components/shells/learning-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  api,
  type LearningNote,
  type PlayerOutline,
  type QAQuestion,
  type SubtopicViewer,
} from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/utils";

type Tab = "overview" | "qa" | "notes" | "resources";

export default function LearnPlayerPage() {
  const params = useParams<{ subjectId: string; subtopicId: string }>();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [viewer, setViewer] = useState<SubtopicViewer | null>(null);
  const [outline, setOutline] = useState<PlayerOutline | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [timeSpent, setTimeSpent] = useState(0);
  const [canComplete, setCanComplete] = useState(false);
  const [minTime, setMinTime] = useState(0);
  const [questions, setQuestions] = useState<QAQuestion[]>([]);
  const [notes, setNotes] = useState<LearningNote[]>([]);
  const [qTitle, setQTitle] = useState("");
  const [qBody, setQBody] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [speed, setSpeed] = useState(1);
  const [autoplayNext, setAutoplayNext] = useState(true);
  const [countdown, setCountdown] = useState<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    const [v, o] = await Promise.all([
      api.getSubtopicViewer(params.subtopicId),
      api.getPlayerOutline(params.subjectId),
    ]);
    setViewer(v);
    setOutline(o);
    setTimeSpent(v.progress.time_spent_s);
    setCanComplete(v.progress.can_complete);
    setMinTime(v.progress.min_time_s);
  }, [params.subjectId, params.subtopicId]);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [user, loading, load, router]);

  useEffect(() => {
    if (!viewer) return;
    heartbeatRef.current = setInterval(() => {
      const pos = videoRef.current ? Math.floor(videoRef.current.currentTime) : undefined;
      void api
        .heartbeat(params.subtopicId, { delta_s: 5, position_s: pos })
        .then((res) => {
          setTimeSpent(res.time_spent_s);
          setCanComplete(res.can_complete);
          setMinTime(res.min_time_s);
        })
        .catch(() => undefined);
    }, 5000);
    return () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
    };
  }, [viewer, params.subtopicId]);

  useEffect(() => {
    if (!viewer?.content?.playback || !videoRef.current) return;
    const resume = viewer.video_progress?.resume_position_s ?? 0;
    if (resume > 0) {
      videoRef.current.currentTime = resume;
    }
  }, [viewer]);

  async function loadQA() {
    const rows = await api.listQA(params.subjectId, { subtopic: params.subtopicId });
    setQuestions(rows);
  }

  async function loadNotes() {
    setNotes(await api.listNotes(params.subtopicId));
  }

  useEffect(() => {
    if (tab === "qa") void loadQA().catch((err: ApiError) => toast.error(err.message));
    if (tab === "notes") void loadNotes().catch((err: ApiError) => toast.error(err.message));
  }, [tab, params.subjectId, params.subtopicId]);

  const remaining = Math.max(0, minTime - timeSpent);
  const ringPct = minTime > 0 ? Math.min(100, Math.round((timeSpent / minTime) * 100)) : 100;

  async function markComplete() {
    try {
      await api.completeSubtopic(params.subtopicId);
      toast.success("Marked complete");
      await load();
      if (autoplayNext && viewer?.next_subtopic_id) {
        setCountdown(5);
      }
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  useEffect(() => {
    if (countdown == null) return;
    if (countdown <= 0) {
      if (viewer?.next_subtopic_id) {
        router.push(`/learn/${params.subjectId}/${viewer.next_subtopic_id}`);
      }
      return;
    }
    const t = setTimeout(() => setCountdown((c) => (c == null ? null : c - 1)), 1000);
    return () => clearTimeout(t);
  }, [countdown, viewer, params.subjectId, router]);

  const playbackSrc = useMemo(() => {
    const pb = viewer?.content?.playback;
    if (!pb?.playback_id) return null;
    // Mux HLS stream; token appended when signed
    const token = pb.token && pb.token !== pb.playback_id ? `?token=${pb.token}` : "";
    return `https://stream.mux.com/${pb.playback_id}.m3u8${token}`;
  }, [viewer]);

  if (!viewer) {
    return <p className="p-8 text-sm text-[var(--muted-foreground)]">Loading player…</p>;
  }

  const content = viewer.content;

  return (
    <LearningShell
      subjectId={params.subjectId}
      subjectTitle={viewer.subject.title}
      progressPercent={outline?.percent ?? 0}
      completedCount={outline?.completed_count ?? 0}
      totalCount={outline?.total_count ?? 0}
      currentSubtopicId={params.subtopicId}
      outline={outline}
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3 text-[var(--ink-foreground)]">
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="border-white/20 text-inherit"
              disabled={!viewer.prev_subtopic_id}
              onClick={() =>
                viewer.prev_subtopic_id &&
                router.push(`/learn/${params.subjectId}/${viewer.prev_subtopic_id}`)
              }
            >
              Previous
            </Button>
            <Button
              variant="outline"
              className="border-white/20 text-inherit"
              disabled={!viewer.next_subtopic_id}
              onClick={() =>
                viewer.next_subtopic_id &&
                router.push(`/learn/${params.subjectId}/${viewer.next_subtopic_id}`)
              }
            >
              Next
            </Button>
          </div>
          <div className="flex items-center gap-3">
            {!viewer.progress.completed ? (
              <div className="flex items-center gap-2 text-xs">
                <div className="relative h-8 w-8 rounded-full border border-white/30">
                  <span className="absolute inset-0 flex items-center justify-center">{ringPct}%</span>
                </div>
                {remaining > 0 ? <span>{remaining}s left</span> : <span>Ready</span>}
              </div>
            ) : null}
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={viewer.progress.completed || false}
                disabled={!canComplete && !viewer.progress.completed}
                onChange={() => {
                  if (!viewer.progress.completed) void markComplete();
                }}
              />
              Mark as complete
            </label>
          </div>
        </div>
      }
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        <div>
          <h1 className="font-display text-2xl">{viewer.subtopic.title}</h1>
          <p className="text-sm opacity-70">{viewer.subtopic.kind}</p>
        </div>

        {viewer.subtopic.kind === "quiz" ? (
          <QuizTake
            subtopicId={params.subtopicId}
            onComplete={() => {
              void markComplete().catch(() => undefined);
            }}
          />
        ) : content?.content_type === "video" || content?.content_type === "video_slides" ? (
          <div className="overflow-hidden rounded-lg bg-black">
            {playbackSrc ? (
              <video
                ref={videoRef}
                className="aspect-video w-full"
                controls
                playsInline
                src={playbackSrc}
                onRateChange={(e) => setSpeed((e.target as HTMLVideoElement).playbackRate)}
                onPause={() => {
                  const el = videoRef.current;
                  if (!el) return;
                  void api.putVideoProgress(params.subtopicId, {
                    position_s: Math.floor(el.currentTime),
                    duration_s: Math.floor(el.duration || content.duration_s || 0),
                    rate: el.playbackRate,
                    client_ts: Date.now(),
                  });
                }}
              />
            ) : (
              <div className="flex aspect-video items-center justify-center text-sm text-white/70">
                Video processing… ({content?.playback?.status || content?.processing_status})
              </div>
            )}
            <div className="flex flex-wrap items-center gap-3 border-t border-white/10 px-3 py-2 text-xs text-white/80">
              <label className="flex items-center gap-1">
                Speed
                <select
                  className="rounded bg-black/40 px-1"
                  value={speed}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setSpeed(v);
                    if (videoRef.current) videoRef.current.playbackRate = v;
                  }}
                >
                  {[0.75, 1, 1.25, 1.5, 1.75, 2].map((s) => (
                    <option key={s} value={s}>
                      {s}x
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={autoplayNext}
                  onChange={(e) => setAutoplayNext(e.target.checked)}
                />
                Autoplay next
              </label>
              {countdown != null ? (
                <span>
                  Next in {countdown}s…{" "}
                  <button type="button" className="underline" onClick={() => setCountdown(null)}>
                    Cancel
                  </button>
                </span>
              ) : null}
            </div>
          </div>
        ) : content?.content_type === "article" ? (
          <article
            className="mx-auto max-w-[68ch] rounded-lg bg-[var(--card)] p-6 text-[var(--foreground)] prose prose-sm"
            dangerouslySetInnerHTML={{ __html: String(content.body_json?.html ?? "") }}
          />
        ) : content?.preview_url || content?.file_url ? (
          <div className="overflow-hidden rounded-lg bg-[var(--card)]">
            <iframe
              title={content.title || "Document"}
              src={content.preview_url || content.file_url || ""}
              className="h-[70vh] w-full bg-white"
            />
            {content.file_url ? (
              <div className="border-t p-2 text-sm text-[var(--foreground)]">
                <a className="underline" href={content.file_url} target="_blank" rel="noreferrer">
                  Download original
                </a>
              </div>
            ) : null}
          </div>
        ) : content?.external_url ? (
          <div className="rounded-lg bg-[var(--card)] p-6 text-[var(--foreground)]">
            <a className="underline" href={content.external_url} target="_blank" rel="noreferrer">
              Open link / live session
            </a>
          </div>
        ) : (
          <div className="rounded-lg bg-black/40 p-8 text-center text-sm opacity-80">
            No content attached yet for this subtopic.
          </div>
        )}

        <div className="rounded-lg bg-[var(--card)] text-[var(--foreground)]">
          <div className="flex flex-wrap gap-1 border-b border-[var(--border)] p-2">
            {(
              [
                ["overview", "Overview"],
                ["qa", "Q&A"],
                ["notes", "Notes"],
                ["resources", "Resources"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={cn(
                  "rounded-md px-3 py-2 text-sm",
                  tab === id ? "bg-[var(--secondary)] font-medium" : "text-[var(--muted-foreground)]",
                )}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="p-4">
            {tab === "overview" ? (
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{
                  __html: String(viewer.subject.description_json?.html ?? "<p>No overview yet.</p>"),
                }}
              />
            ) : null}

            {tab === "resources" ? (
              <ul className="space-y-2 text-sm">
                {viewer.resources.length === 0 ? (
                  <li className="text-[var(--muted-foreground)]">No resources.</li>
                ) : (
                  viewer.resources.map((r) => (
                    <li key={r.id}>
                      <a
                        className="underline"
                        href={r.url || r.file_url || "#"}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {r.title}
                      </a>
                    </li>
                  ))
                )}
              </ul>
            ) : null}

            {tab === "qa" ? (
              <div className="space-y-4">
                <form
                  className="space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void api
                      .askQuestion(params.subjectId, {
                        title: qTitle,
                        body: qBody,
                        subtopic_id: params.subtopicId,
                      })
                      .then(() => {
                        setQTitle("");
                        setQBody("");
                        return loadQA();
                      })
                      .catch((err: ApiError) => toast.error(err.message));
                  }}
                >
                  <Input placeholder="Question title" value={qTitle} onChange={(e) => setQTitle(e.target.value)} />
                  <textarea
                    className="min-h-20 w-full rounded-md border border-[var(--border)] bg-transparent p-2 text-sm"
                    placeholder="Details"
                    value={qBody}
                    onChange={(e) => setQBody(e.target.value)}
                  />
                  <Button type="submit" size="sm">
                    Ask
                  </Button>
                </form>
                <ul className="space-y-3">
                  {questions.map((q) => (
                    <li key={q.id} className="rounded-md border border-[var(--border)] p-3">
                      <p className="font-medium">{q.title}</p>
                      <p className="text-sm text-[var(--muted-foreground)]">{q.body}</p>
                      <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                        {q.author_name}
                        {q.is_resolved ? " · Resolved" : ""}
                      </p>
                      <ul className="mt-2 space-y-1 text-sm">
                        {q.answers.map((a) => (
                          <li key={a.id} className="rounded bg-[var(--muted)]/40 px-2 py-1">
                            {a.body}{" "}
                            <span className="text-xs text-[var(--muted-foreground)]">
                              — {a.author_name}
                              {a.is_instructor ? " (instructor)" : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {tab === "notes" ? (
              <div className="space-y-3">
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const ts = videoRef.current ? Math.floor(videoRef.current.currentTime) : null;
                    void api
                      .createNote(params.subtopicId, { body: noteBody, timestamp_s: ts })
                      .then(() => {
                        setNoteBody("");
                        return loadNotes();
                      })
                      .catch((err: ApiError) => toast.error(err.message));
                  }}
                >
                  <Input
                    placeholder="Add a note…"
                    value={noteBody}
                    onChange={(e) => setNoteBody(e.target.value)}
                  />
                  <Button type="submit" size="sm">
                    Save
                  </Button>
                </form>
                <ul className="space-y-2 text-sm">
                  {notes.map((n) => (
                    <li key={n.id} className="flex items-start justify-between gap-2 rounded border border-[var(--border)] p-2">
                      <div>
                        {n.timestamp_s != null ? (
                          <button
                            type="button"
                            className="mr-2 text-xs text-[var(--primary)] underline"
                            onClick={() => {
                              if (videoRef.current) videoRef.current.currentTime = n.timestamp_s || 0;
                            }}
                          >
                            {Math.floor((n.timestamp_s || 0) / 60)}:
                            {String((n.timestamp_s || 0) % 60).padStart(2, "0")}
                          </button>
                        ) : null}
                        {n.body}
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          void api.deleteNote(n.id).then(loadNotes).catch((err: ApiError) => toast.error(err.message))
                        }
                      >
                        Delete
                      </Button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>

        <p className="text-center text-xs opacity-60">
          <Link href={`/subjects/${viewer.subject.slug}`} className="underline">
            Subject landing
          </Link>
        </p>
      </div>
    </LearningShell>
  );
}
