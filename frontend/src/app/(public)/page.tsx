import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <section className="relative overflow-hidden rounded-[calc(var(--radius)+0.25rem)] border bg-[radial-gradient(circle_at_top_right,_rgba(200,148,58,0.18),_transparent_45%),linear-gradient(180deg,_#f7f4ec_0%,_var(--background)_70%)] px-6 py-16 md:px-12 md:py-24">
      <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(var(--border)_1px,transparent_1px)] [background-size:18px_18px]" />
      <div className="relative max-w-2xl">
        <p className="font-display text-sm font-semibold tracking-[0.08em] text-[var(--primary)] uppercase">
          Imo Ijinle Academy
        </p>
        <h1 className="mt-4 font-display text-4xl leading-tight text-[var(--foreground)] md:text-5xl">
          Learn with calm authority
        </h1>
        <p className="mt-4 max-w-xl text-base text-[var(--muted-foreground)] md:text-lg">
          The Spirit Science portal for cohorts, classes, and subjects — built for serious study
          across every device.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/apply/demo">Apply to a cohort</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
