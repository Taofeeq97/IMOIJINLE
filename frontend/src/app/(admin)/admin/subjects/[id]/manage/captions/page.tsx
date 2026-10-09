"use client";

export default function CaptionsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="font-display text-2xl">Captions</h2>
      <p className="text-sm text-[var(--muted-foreground)]">
        Optional for M3. Upload .vtt/.srt per video in a later pass; auto-transcript hooks will
        attach to Mux assets. Caption status shows on each video content block.
      </p>
    </div>
  );
}
