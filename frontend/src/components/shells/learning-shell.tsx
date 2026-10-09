"use client";

import Link from "next/link";
import { ChevronLeft, List, Lock } from "lucide-react";
import { useState } from "react";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { PlayerOutline } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function LearningShell({
  children,
  subjectId,
  subjectTitle = "Subject",
  progressPercent = 0,
  completedCount = 0,
  totalCount = 0,
  currentSubtopicId,
  outline,
  footer,
}: {
  children: React.ReactNode;
  subjectId: string;
  subjectTitle?: string;
  progressPercent?: number;
  completedCount?: number;
  totalCount?: number;
  currentSubtopicId?: string;
  outline?: PlayerOutline | null;
  footer?: React.ReactNode;
}) {
  const [outlineOpen, setOutlineOpen] = useState(false);

  const outlineNode = (
    <div className="space-y-3 text-sm">
      <p className="font-medium">Subject content</p>
      <p className="text-xs text-[var(--muted-foreground)]">
        {completedCount} of {totalCount} complete
      </p>
      {(outline?.topics ?? []).map((topic) => (
        <div key={topic.id} className="rounded-lg border p-3">
          <p className="text-[var(--muted-foreground)]">
            {topic.title}{" "}
            <span className="text-xs">
              {topic.completed_count}/{topic.total_count} · {Math.round(topic.total_time_s / 60)}m
            </span>
          </p>
          <ul className="mt-2 space-y-1">
            {topic.subtopics.map((s) => {
              const active = s.id === currentSubtopicId;
              return (
                <li key={s.id}>
                  {s.locked ? (
                    <div className="flex items-center gap-2 px-2 py-2 text-[var(--muted-foreground)]">
                      <Lock className="h-3.5 w-3.5" />
                      <span>{s.title}</span>
                    </div>
                  ) : (
                    <Link
                      href={`/learn/${subjectId}/${s.id}`}
                      className={cn(
                        "flex items-center gap-2 rounded-md px-2 py-2",
                        active
                          ? "border-l-2 border-[var(--accent)] bg-[var(--secondary)]/60 font-medium"
                          : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
                      )}
                    >
                      <input type="checkbox" readOnly checked={s.completed} className="pointer-events-none" />
                      <span className="truncate">{s.title}</span>
                      <span className="ml-auto text-[10px]">{Math.round(s.estimated_time_s / 60)}m</span>
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex min-h-dvh flex-col bg-[var(--background)]">
      <header className="flex h-14 items-center gap-3 bg-[var(--ink)] px-4 text-[var(--ink-foreground)]">
        <Link href="/learning" className="inline-flex min-h-11 items-center gap-1 text-sm">
          <ChevronLeft className="h-4 w-4" />
          My learning
        </Link>
        <p className="min-w-0 flex-1 truncate text-sm font-medium">{subjectTitle}</p>
        <div
          className="relative h-9 w-9 rounded-full border border-[var(--ink-foreground)]/30"
          title={`${completedCount} of ${totalCount} complete`}
          aria-label={`${progressPercent}% complete`}
        >
          <span className="absolute inset-0 flex items-center justify-center text-[10px]">
            {progressPercent}%
          </span>
        </div>
        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center rounded-lg lg:hidden"
          onClick={() => setOutlineOpen(true)}
          aria-label="Subject content"
        >
          <List className="h-5 w-5" />
        </button>
      </header>
      <div className="flex min-h-0 flex-1">
        <main className="flex min-w-0 flex-1 flex-col bg-[var(--ink-2)] text-[var(--ink-foreground)]">
          <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">{children}</div>
          {footer ? (
            <div className="border-t border-white/10 bg-[var(--ink)] px-4 py-3">{footer}</div>
          ) : null}
        </main>
        <aside className="hidden w-[380px] shrink-0 overflow-y-auto border-l bg-[var(--card)] p-4 text-[var(--foreground)] lg:block">
          {outlineNode}
        </aside>
      </div>
      <Sheet open={outlineOpen} onOpenChange={setOutlineOpen}>
        <SheetContent side="bottom" className="max-h-[80dvh] overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Subject content</SheetTitle>
          </SheetHeader>
          {outlineNode}
        </SheetContent>
      </Sheet>
    </div>
  );
}
