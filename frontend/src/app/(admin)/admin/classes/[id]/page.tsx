"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, type ClassItem, type ClassSubjectLink, type Subject } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";

export default function ClassDetailPage() {
  const params = useParams<{ id: string }>();
  const [klass, setKlass] = useState<ClassItem | null>(null);
  const [links, setLinks] = useState<ClassSubjectLink[]>([]);
  const [library, setLibrary] = useState<Subject[]>([]);

  async function load() {
    const [c, s, subjects] = await Promise.all([
      api.getClass(params.id),
      api.listClassSubjects(params.id),
      api.listSubjects(),
    ]);
    setKlass(c);
    setLinks(s);
    setLibrary(subjects.results);
  }

  useEffect(() => {
    void load().catch((err: ApiError) => toast.error(err.message));
  }, [params.id]);

  async function publish() {
    try {
      setKlass(await api.publishClass(params.id));
      toast.success("Class published");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  async function attach(subjectId: string) {
    try {
      await api.attachSubject(params.id, subjectId, "linked");
      toast.success("Subject attached");
      await load();
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  if (!klass) return <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>;

  const attached = new Set(links.map((l) => l.subject));

  return (
    <>
      <PageHeader
        title={klass.name}
        description={`Cohort: ${klass.cohort_name}`}
        actions={<Button onClick={() => void publish()}>Publish</Button>}
      />
      <Badge className="mb-6">{klass.status}</Badge>

      <h2 className="mb-3 font-medium">Subjects</h2>
      <ul className="mb-8 space-y-2">
        {links.map((l) => (
          <li key={l.id} className="rounded-[var(--radius)] border bg-[var(--card)] px-4 py-3">
            <Link href={`/admin/subjects/${l.subject}`} className="font-medium underline">
              {l.subject_title}
            </Link>
            <p className="text-xs text-[var(--muted-foreground)]">
              {l.mode} · {l.subject_status}
            </p>
          </li>
        ))}
      </ul>

      <h3 className="mb-2 text-sm font-medium text-[var(--muted-foreground)]">Add from library</h3>
      <ul className="space-y-2">
        {library
          .filter((s) => !attached.has(s.id))
          .map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between gap-3 rounded-[var(--radius)] border px-4 py-3"
            >
              <span>{s.title}</span>
              <Button size="sm" variant="outline" onClick={() => void attach(s.id)}>
                Attach
              </Button>
            </li>
          ))}
      </ul>
    </>
  );
}
