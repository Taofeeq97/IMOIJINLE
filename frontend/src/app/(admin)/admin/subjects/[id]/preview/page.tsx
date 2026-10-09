"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import type { ApiError } from "@/lib/api/schema";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type PreviewPayload = {
  title: string;
  subtitle: string;
  status: string;
  level: string;
  description_json?: { html?: string };
  intended_learners?: { learn?: string[]; requirements?: string[]; audience?: string[] };
  curriculum?: {
    title: string;
    subtopics: { title: string; kind: string; content_type: string | null; estimated_time_s: number }[];
  }[];
  preview?: boolean;
};

function PreviewInner() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const token = search.get("token") ?? "";
  const [data, setData] = useState<PreviewPayload | null>(null);

  useEffect(() => {
    void fetch(`${API_URL}/api/v1/public/subjects/${params.id}/preview?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        const body = await res.json();
        if (!res.ok) throw body;
        return body as PreviewPayload;
      })
      .then(setData)
      .catch((err: ApiError) => toast.error(err.message ?? "Preview failed"));
  }, [params.id, token]);

  if (!data) return <p className="p-8 text-sm text-[var(--muted-foreground)]">Loading preview…</p>;

  return (
    <div className="min-h-dvh bg-[var(--background)]">
      <div className="bg-[var(--ink,#14201C)] px-4 py-8 text-[var(--ink-foreground,#F4F2EC)]">
        <p className="text-xs uppercase tracking-wide opacity-70">Preview as student</p>
        <h1 className="mt-2 font-display text-3xl">{data.title}</h1>
        <p className="mt-1 opacity-80">{data.subtitle}</p>
        <div className="mt-3 flex gap-2">
          <Badge className="bg-white/15 text-white">{data.level}</Badge>
          <Badge className="bg-white/15 text-white">{data.status}</Badge>
        </div>
      </div>
      <div className="mx-auto grid max-w-5xl gap-8 px-4 py-8 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-6">
          <section>
            <h2 className="mb-2 font-display text-xl">What you&apos;ll learn</h2>
            <ul className="grid gap-2 sm:grid-cols-2">
              {(data.intended_learners?.learn ?? []).map((item) => (
                <li key={item} className="rounded-md border border-[var(--border)] px-3 py-2 text-sm">
                  {item}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2 className="mb-2 font-display text-xl">Description</h2>
            <div
              className="prose prose-sm max-w-none text-sm"
              dangerouslySetInnerHTML={{ __html: data.description_json?.html || "<p></p>" }}
            />
          </section>
        </div>
        <aside className="space-y-4">
          <h2 className="font-display text-xl">Subject content</h2>
          {(data.curriculum ?? []).map((topic) => (
            <div key={topic.title} className="rounded-lg border border-[var(--border)] p-3">
              <p className="font-medium">{topic.title}</p>
              <ul className="mt-2 space-y-1 text-sm text-[var(--muted-foreground)]">
                {topic.subtopics.map((s) => (
                  <li key={s.title}>
                    {s.title} · {s.kind}
                    {s.content_type ? ` · ${s.content_type}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </aside>
      </div>
    </div>
  );
}

export default function SubjectPreviewPage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm">Loading…</p>}>
      <PreviewInner />
    </Suspense>
  );
}
