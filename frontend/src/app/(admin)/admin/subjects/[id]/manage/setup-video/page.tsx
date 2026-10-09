"use client";

export default function SetupVideoPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="font-display text-2xl">Setup & test video</h2>
      <p className="text-sm text-[var(--muted-foreground)]">
        Prefer 1080p, clear audio, and captions. Videos upload directly to Mux from Curriculum
        (Edit → Video). Processing status updates via Mux webhooks.
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted-foreground)]">
        <li>Stable framing and lighting</li>
        <li>Test playback on mobile data</li>
        <li>Keep intro under 2 minutes for orientation clips</li>
      </ul>
    </div>
  );
}
