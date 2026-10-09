"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type LearningClassGroup, type LearningSubjectCard } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { useAuth } from "@/lib/auth/auth-context";

type Tab = "subjects" | "classes" | "notes";

export default function LearningPage() {
  const { user, loading } = useAuth();
  const [tab, setTab] = useState<Tab>("subjects");
  const [subjects, setSubjects] = useState<LearningSubjectCard[]>([]);
  const [classes, setClasses] = useState<LearningClassGroup[]>([]);
  const [cont, setCont] = useState<LearningSubjectCard | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    void api
      .myLearning()
      .then((data) => {
        setSubjects(data.subjects);
        setClasses(data.classes);
        setCont(data.continue);
      })
      .catch((err: ApiError) => toast.error(err.message))
      .finally(() => setReady(true));
  }, [user, loading]);

  const tabs = useMemo(
    () =>
      [
        { id: "subjects" as const, label: "All subjects" },
        { id: "classes" as const, label: "My classes" },
        { id: "notes" as const, label: "Notes" },
      ] as const,
    [],
  );

  return (
    <>
      <PageHeader
        title="My learning"
        description="Continue subjects from your admitted classes."
        actions={
          <Button asChild variant="outline">
            <Link href="/portal">Applications</Link>
          </Button>
        }
      />

      {cont ? (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Continue where you left off
            </p>
            <p className="font-medium">{cont.title}</p>
            <p className="text-xs text-[var(--muted-foreground)]">
              {cont.class_name} · {cont.percent}% complete
            </p>
          </div>
          <Button asChild>
            <Link
              href={
                cont.continue_subtopic_id
                  ? `/learn/${cont.subject_id}/${cont.continue_subtopic_id}`
                  : `/subjects/${cont.subject_slug}`
              }
            >
              Continue
            </Link>
          </Button>
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Button
            key={t.id}
            size="sm"
            variant={tab === t.id ? "default" : "outline"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </Button>
        ))}
      </div>

      {!ready ? (
        <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
      ) : tab === "notes" ? (
        <EmptyState
          title="Notes live in the player"
          description="Open a subject and use the Notes tab while learning."
        />
      ) : tab === "classes" ? (
        classes.length === 0 ? (
          <EmptyState title="No classes yet" description="Admission to a class unlocks subjects here." />
        ) : (
          <div className="space-y-6">
            {classes.map((c) => (
              <section key={c.enrollment_id}>
                <h2 className="mb-3 font-display text-xl">
                  {c.class_name}{" "}
                  <span className="text-sm font-normal text-[var(--muted-foreground)]">
                    · {c.cohort_name}
                  </span>
                </h2>
                <SubjectGrid items={c.subjects} />
              </section>
            ))}
          </div>
        )
      ) : subjects.length === 0 ? (
        <EmptyState
          title="No subjects yet"
          description="When an admin admits you to a class, subjects appear here."
        />
      ) : (
        <SubjectGrid items={subjects} />
      )}
    </>
  );
}

function SubjectGrid({ items }: { items: LearningSubjectCard[] }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((s) => (
        <li
          key={`${s.class_id}-${s.subject_id}`}
          className="group overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--card)]"
        >
          <div className="aspect-video bg-[var(--muted)]">
            {s.cover_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={s.cover_image_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-[var(--muted-foreground)]">
                {s.title}
              </div>
            )}
          </div>
          <div className="space-y-2 p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Link href={`/subjects/${s.subject_slug}`} className="font-medium hover:underline">
                  {s.title}
                </Link>
                <p className="text-xs text-[var(--muted-foreground)]">{s.class_name}</p>
              </div>
              <Badge>{s.level}</Badge>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[var(--muted)]">
              <div className="h-full bg-[var(--primary)]" style={{ width: `${s.percent}%` }} />
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-[var(--muted-foreground)]">{s.percent}% complete</span>
              <Button asChild size="sm" className="opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
                <Link
                  href={
                    s.continue_subtopic_id
                      ? `/learn/${s.subject_id}/${s.continue_subtopic_id}`
                      : `/subjects/${s.subject_slug}`
                  }
                >
                  {s.percent > 0 ? "Continue" : "Start"}
                </Link>
              </Button>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
