"use client";

export default function AccessibilityPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <h2 className="font-display text-2xl">Accessibility</h2>
      <p className="text-sm text-[var(--muted-foreground)]">
        Prefer captions on by default, describe images in articles, and keep curriculum titles
        clear for screen readers. Keyboard move up/down is available via reorder APIs.
      </p>
    </div>
  );
}
