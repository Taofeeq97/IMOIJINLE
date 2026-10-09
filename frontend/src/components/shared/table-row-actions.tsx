"use client";

import Link from "next/link";
import { MoreHorizontal, Pencil, Trash2, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type TableActionItem = {
  label: string;
  onSelect?: () => void;
  href?: string;
  icon?: LucideIcon;
  destructive?: boolean;
  separatorBefore?: boolean;
};

type TableRowActionsProps = {
  onEdit?: () => void;
  onDelete?: () => void;
  editLabel?: string;
  deleteLabel?: string;
  items?: TableActionItem[];
  className?: string;
  disabled?: boolean;
};

export function TableRowActions({
  onEdit,
  onDelete,
  editLabel = "Edit",
  deleteLabel = "Delete",
  items = [],
  className,
  disabled,
}: TableRowActionsProps) {
  const actions: TableActionItem[] = [
    ...items,
    ...(onEdit ? [{ label: editLabel, onSelect: onEdit, icon: Pencil }] : []),
    ...(onDelete
      ? [{ label: deleteLabel, onSelect: onDelete, icon: Trash2, destructive: true, separatorBefore: true }]
      : []),
  ];

  if (actions.length === 0) return null;

  return (
    <div className={cn("flex justify-end", className)}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            disabled={disabled}
            className="h-8 w-8"
            aria-label="Row actions"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          {actions.map((action) => {
            const Icon = action.icon;
            const content = (
              <>
                {Icon ? <Icon className="h-4 w-4" /> : null}
                {action.label}
              </>
            );
            return (
              <div key={action.label}>
                {action.separatorBefore ? <DropdownMenuSeparator /> : null}
                {action.href ? (
                  <DropdownMenuItem asChild className={action.destructive ? "text-[var(--destructive)]" : undefined}>
                    <Link href={action.href}>{content}</Link>
                  </DropdownMenuItem>
                ) : (
                  <DropdownMenuItem
                    className={action.destructive ? "text-[var(--destructive)]" : undefined}
                    onSelect={(e) => {
                      e.preventDefault();
                      action.onSelect?.();
                    }}
                  >
                    {content}
                  </DropdownMenuItem>
                )}
              </div>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
