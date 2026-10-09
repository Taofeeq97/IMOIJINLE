"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type Column<T> = {
  id: string;
  header: string;
  cell: (row: T) => React.ReactNode;
  priority?: "high" | "medium" | "low";
  align?: "left" | "right";
  className?: string;
};

type ResponsiveTableProps<T> = {
  columns: Column<T>[];
  data: T[];
  getRowId: (row: T) => string;
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  loading?: boolean;
  emptyMessage?: string;
  emptyDescription?: string;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
};

export function ResponsiveTable<T>({
  columns,
  data,
  getRowId,
  title,
  description,
  actions,
  loading,
  emptyMessage = "Nothing here yet.",
  emptyDescription,
  error,
  onRetry,
  className,
}: ResponsiveTableProps<T>) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--radius)] border border-[var(--border)] bg-[var(--card)]",
        className,
      )}
    >
      {(title || description || actions) && (
        <div className="flex flex-col gap-3 border-b border-[var(--border)] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            {title ? (
              <h2 className="font-display text-lg font-semibold tracking-tight text-[var(--foreground)]">
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="mt-0.5 text-sm text-[var(--muted-foreground)]">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      )}

      {loading ? (
        <div className="space-y-3 p-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : error ? (
        <div className="p-6 text-sm">
          <p className="text-[var(--destructive)]">{error}</p>
          {onRetry ? (
            <button type="button" className="mt-3 underline" onClick={onRetry}>
              Retry
            </button>
          ) : null}
        </div>
      ) : data.length === 0 ? (
        <div className="px-4 py-12 text-center">
          <p className="text-sm font-medium">{emptyMessage}</p>
          {emptyDescription ? (
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">{emptyDescription}</p>
          ) : null}
        </div>
      ) : (
        <>
          <div className="space-y-3 p-3 md:hidden">
            {data.map((row) => (
              <div
                key={getRowId(row)}
                className="rounded-[calc(var(--radius)-2px)] border border-[var(--border)] bg-[var(--background)] p-3"
              >
                {columns
                  .filter((c) => c.priority !== "low")
                  .map((col) => (
                    <div key={col.id} className="flex items-start justify-between gap-4 py-1.5 text-sm">
                      <span className="text-[var(--muted-foreground)]">{col.header}</span>
                      <span className="max-w-[65%] text-right font-medium">{col.cell(row)}</span>
                    </div>
                  ))}
              </div>
            ))}
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--muted)]/35">
                  {columns.map((col) => (
                    <th
                      key={col.id}
                      className={cn(
                        "px-4 py-3 text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]",
                        col.align === "right" && "text-right",
                        col.priority === "low" && "hidden lg:table-cell",
                        col.priority === "medium" && "hidden xl:table-cell lg:table-cell",
                        col.className,
                      )}
                    >
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr
                    key={getRowId(row)}
                    className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--muted)]/25"
                  >
                    {columns.map((col) => (
                      <td
                        key={col.id}
                        className={cn(
                          "px-4 py-3 align-middle text-[var(--foreground)]",
                          col.align === "right" && "text-right",
                          col.priority === "low" && "hidden lg:table-cell",
                          col.className,
                        )}
                      >
                        {col.cell(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
