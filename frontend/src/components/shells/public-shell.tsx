"use client";

import Link from "next/link";

import { UserMenu } from "@/components/shared/user-menu";
import { Button } from "@/components/ui/button";

export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b border-[var(--border)]/70 bg-[var(--background)]/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between gap-4 px-4">
          <Link href="/" className="font-display text-lg font-semibold tracking-tight">
            Imo Ijinle Academy
          </Link>
          <nav className="hidden items-center gap-6 text-sm md:flex">
            <Link href="/cohorts" className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Cohorts
            </Link>
            <Link href="/pages/about" className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              About
            </Link>
            <Link href="/verify/demo" className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              Verify
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <Button asChild size="sm" variant="outline" className="hidden sm:inline-flex">
              <Link href="/apply/demo">Apply</Link>
            </Button>
            <UserMenu />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-8">{children}</main>
      <footer className="border-t bg-[var(--muted)]/40">
        <div className="mx-auto flex max-w-[1200px] flex-col gap-2 px-4 py-8 text-sm text-[var(--muted-foreground)] md:flex-row md:justify-between">
          <p>© {new Date().getFullYear()} Imo Ijinle Academy</p>
          <div className="flex gap-4">
            <span>Medical</span>
            <span>Innovation</span>
            <span>Business</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
