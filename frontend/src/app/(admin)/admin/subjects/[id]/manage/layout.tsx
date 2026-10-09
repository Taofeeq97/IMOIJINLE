"use client";

import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, Circle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Subject, type SubjectChecklist } from "@/lib/api/client";
import type { ApiError } from "@/lib/api/schema";
import { cn } from "@/lib/utils";

type ManageCtx = {
  subject: Subject | null;
  checklist: SubjectChecklist | null;
  refresh: () => Promise<void>;
  savedAt: string | null;
  markSaved: () => void;
};

const Ctx = createContext<ManageCtx | null>(null);

export function useSubjectManage() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSubjectManage must be used in manage layout");
  return ctx;
}

const NAV = [
  {
    group: "Plan your subject",
    items: [
      { key: "intended_learners", href: "intended-learners", label: "Intended learners" },
      { key: "subject_structure", href: "structure", label: "Subject structure" },
      { key: "setup_test_video", href: "setup-video", label: "Setup & test video" },
    ],
  },
  {
    group: "Create your content",
    items: [
      { key: "film_edit", href: "film-edit", label: "Film & edit" },
      { key: "curriculum", href: "curriculum", label: "Curriculum" },
      { key: "captions", href: "captions", label: "Captions" },
      { key: "accessibility", href: "accessibility", label: "Accessibility" },
    ],
  },
  {
    group: "Publish your subject",
    items: [
      { key: "landing_page", href: "landing", label: "Subject landing page" },
      { key: "pricing", href: "pricing", label: "Access & pricing" },
      { key: "promotions", href: "promotions", label: "Promotions" },
      { key: "messages", href: "messages", label: "Subject messages" },
    ],
  },
  {
    group: "Settings",
    items: [{ key: "settings", href: "settings", label: "Settings" }],
  },
];

export default function SubjectManageLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [checklist, setChecklist] = useState<SubjectChecklist | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);

  const refresh = useCallback(async () => {
    const [s, c] = await Promise.all([
      api.getSubject(params.id),
      api.getSubjectChecklist(params.id),
    ]);
    setSubject(s);
    setChecklist(c);
  }, [params.id]);

  useEffect(() => {
    void refresh().catch((err: ApiError) => toast.error(err.message));
  }, [refresh]);

  const markSaved = useCallback(() => {
    setSavedAt(new Date().toLocaleTimeString());
  }, []);

  async function publish() {
    if (!checklist?.can_publish) {
      toast.error(`Missing: ${(checklist?.missing ?? []).join(", ") || "checklist items"}`);
      return;
    }
    setPublishing(true);
    try {
      const s = await api.publishSubject(params.id);
      setSubject(s);
      await refresh();
      toast.success("Subject published");
    } catch (err) {
      toast.error((err as ApiError).message ?? "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  async function preview() {
    try {
      const tok = await api.createPreviewToken(params.id);
      window.open(`/admin/subjects/${params.id}/preview?token=${tok.token}`, "_blank");
    } catch (err) {
      toast.error((err as ApiError).message);
    }
  }

  const value = useMemo(
    () => ({ subject, checklist, refresh, savedAt, markSaved }),
    [subject, checklist, refresh, savedAt, markSaved],
  );

  const base = `/admin/subjects/${params.id}/manage`;

  return (
    <Ctx.Provider value={value}>
      <div className="-mx-4 -mt-2 flex min-h-[calc(100dvh-3.5rem)] flex-col bg-[var(--background)] md:-mx-6">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--card)] px-4 py-3">
          <div className="min-w-0">
            <button
              type="button"
              className="text-xs text-[var(--muted-foreground)] hover:underline"
              onClick={() => router.push("/admin/subjects")}
            >
              ← Subject library
            </button>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h1 className="truncate font-display text-xl font-semibold">
                {subject?.title ?? "Loading…"}
              </h1>
              {subject ? <Badge>{subject.status}</Badge> : null}
              {savedAt ? (
                <span className="text-xs text-[var(--muted-foreground)]">Saved · {savedAt}</span>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void preview()}>
              Preview
            </Button>
            <Button onClick={() => void publish()} disabled={publishing || !checklist?.can_publish}>
              {publishing ? "Publishing…" : "Publish"}
            </Button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1">
          <aside className="hidden w-[260px] shrink-0 overflow-y-auto border-r border-[var(--border)] bg-[var(--card)] p-3 md:block">
            <p className="mb-3 px-2 text-xs text-[var(--muted-foreground)]">
              Checklist {checklist ? `${checklist.progress.completed}/${checklist.progress.total}` : "…"}
            </p>
            <nav className="space-y-5">
              {NAV.map((group) => (
                <div key={group.group}>
                  <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                    {group.group}
                  </p>
                  <ul className="space-y-0.5">
                    {group.items.map((item) => {
                      const href = `${base}/${item.href}`;
                      const active = pathname.startsWith(href);
                      const done = checklist?.items?.[item.key];
                      return (
                        <li key={item.href}>
                          <Link
                            href={href}
                            className={cn(
                              "flex min-h-11 items-center gap-2 rounded-md px-2 text-sm",
                              active
                                ? "bg-[var(--secondary)] font-medium text-[var(--primary)]"
                                : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
                            )}
                          >
                            {done ? (
                              <CheckCircle2 className="h-4 w-4 shrink-0 text-[var(--primary)]" />
                            ) : (
                              <Circle className="h-4 w-4 shrink-0 opacity-50" />
                            )}
                            <span className="truncate">{item.label}</span>
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </nav>
            {checklist?.warnings?.length ? (
              <div className="mt-4 rounded-md border border-[var(--warning)]/40 bg-[var(--warning)]/10 p-2 text-xs text-[var(--foreground)]">
                {checklist.warnings[0]}
              </div>
            ) : null}
          </aside>
          <main className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
        </div>
      </div>
    </Ctx.Provider>
  );
}
