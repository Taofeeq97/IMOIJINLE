import { Button } from "@/components/ui/button";

type EmptyStateProps = {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-[var(--radius)] border border-dashed bg-[var(--card)] px-6 py-16 text-center">
      <h2 className="font-display text-xl text-[var(--foreground)]">{title}</h2>
      {description ? (
        <p className="mt-2 max-w-md text-sm text-[var(--muted-foreground)]">{description}</p>
      ) : null}
      {actionLabel && onAction ? (
        <Button className="mt-6" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
