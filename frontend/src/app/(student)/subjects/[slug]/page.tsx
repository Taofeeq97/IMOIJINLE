"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type SubjectLanding } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

export default function SubjectLandingPage() {
  const params = useParams<{ slug: string }>();
  const { user, loading } = useAuth();
  const [data, setData] = useState<SubjectLanding | null>(null);

  useEffect(() => {
    if (loading || !user) return;
    void api
      .getSubjectLanding(params.slug)
      .then(setData)
      .catch((err: ApiError) => toast.error(err.message));
  }, [params.slug, user, loading]);

  if (!data) {
    return <p className="p-8 text-sm text-[var(--muted-foreground)]">Loading subject…</p>;
  }

  const html = String(data.description_json?.html ?? "");

  return (
    <div className="min-h-dvh bg-[var(--background)]">
      <div className="bg-[var(--ink)] px-4 py-10 text-[var(--ink-foreground)]">
        <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-xs uppercase tracking-wide opacity-70">
              {data.category || "Subject"} · {data.level}
            </p>
            <h1 className="mt-2 font-display text-3xl md:text-4xl">{data.title}</h1>
            <p className="mt-2 opacity-80">{data.subtitle}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge className="bg-white/15 text-white">{data.language}</Badge>
              <Badge className="bg-white/15 text-white">{data.percent}% complete</Badge>
            </div>
            {data.instructors.length ? (
              <p className="mt-4 text-sm opacity-80">
                Instructors: {data.instructors.map((i) => i.name).join(", ")}
              </p>
            ) : null}
          </div>
          <div className="rounded-lg border border-white/10 bg-[var(--ink-2)] p-4">
            <div className="mb-3 aspect-video rounded-md bg-black/40" />
            {data.has_access && data.continue_subtopic_id ? (
              <Button asChild className="w-full">
                <Link href={`/learn/${data.id}/${data.continue_subtopic_id}`}>
                  {data.percent > 0 ? "Continue learning" : "Start learning"}
                </Link>
              </Button>
            ) : (
              <p className="text-sm opacity-80">Enroll in a class that includes this subject to learn.</p>
            )}
            <Button asChild variant="outline" className="mt-2 w-full border-white/20 text-inherit">
              <Link href="/learning">Back to My learning</Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-10 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="space-y-8">
          <section>
            <h2 className="mb-3 font-display text-xl">What you&apos;ll learn</h2>
            <ul className="grid gap-2 sm:grid-cols-2">
              {(data.intended_learners.learn ?? []).map((item) => (
                <li key={item} className="rounded-md border border-[var(--border)] px-3 py-2 text-sm">
                  {item}
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h2 className="mb-3 font-display text-xl">Description</h2>
            <div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: html }} />
          </section>
          <section>
            <h2 className="mb-3 font-display text-xl">Requirements</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted-foreground)]">
              {(data.intended_learners.requirements ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
          <section>
            <h2 className="mb-3 font-display text-xl">Who this is for</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted-foreground)]">
              {(data.intended_learners.audience ?? []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        </div>
        <aside>
          <h2 className="mb-3 font-display text-xl">Subject content</h2>
          <div className="space-y-3">
            {data.curriculum.map((topic) => (
              <details key={topic.id} className="rounded-lg border border-[var(--border)] p-3" open>
                <summary className="cursor-pointer font-medium">
                  {topic.title}{" "}
                  <span className="text-xs font-normal text-[var(--muted-foreground)]">
                    {topic.subtopic_count} items · {Math.round(topic.total_time_s / 60)}m
                  </span>
                </summary>
                <ul className="mt-2 space-y-1 text-sm">
                  {topic.subtopics.map((s) => (
                    <li key={s.id} className="flex items-center justify-between gap-2 py-1">
                      <span>
                        {s.title}
                        {s.is_free_preview ? (
                          <Badge className="ml-2">Preview</Badge>
                        ) : null}
                      </span>
                      {data.has_access || s.is_free_preview ? (
                        <Link className="text-[var(--primary)] underline" href={`/learn/${data.id}/${s.id}`}>
                          Open
                        </Link>
                      ) : (
                        <span className="text-xs text-[var(--muted-foreground)]">Locked</span>
                      )}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
