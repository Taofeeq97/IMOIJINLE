"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { UserMenu } from "@/components/shared/user-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const groups = [
  {
    label: "Operate",
    items: [
      { href: "/admin", label: "Overview" },
      { href: "/admin/cohorts", label: "Cohorts" },
      { href: "/admin/classes", label: "Classes" },
      { href: "/admin/subjects", label: "Subject Library" },
      { href: "/admin/admissions", label: "Admissions" },
      { href: "/admin/grading", label: "Grading" },
      { href: "/admin/announcements", label: "Announcements" },
      { href: "/admin/analytics", label: "Analytics" },
    ],
  },
  {
    label: "Finance & certs",
    items: [
      { href: "/admin/settings/payments", label: "Payment config" },
      { href: "/admin/finance", label: "Finance" },
      { href: "/admin/certificates", label: "Certificates" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/admin/settings", label: "Settings" },
      { href: "/admin/settings/oidc", label: "SSO / OIDC" },
    ],
  },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-dvh bg-[var(--background)]">
      <aside className="hidden w-64 shrink-0 border-r border-[var(--border)] bg-[var(--card)] p-4 md:block">
        <div className="flex items-center justify-between gap-2">
          <Link href="/admin" className="font-display text-lg font-semibold">
            Academy Admin
          </Link>
          <Badge className="bg-[var(--warning)]/15 text-[var(--warning)]">Local</Badge>
        </div>
        <nav className="mt-8 space-y-6">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="mb-2 px-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active =
                    item.href === "/admin"
                      ? pathname === "/admin"
                      : pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex min-h-11 items-center rounded-lg px-3 text-sm",
                        active
                          ? "bg-[var(--secondary)] font-medium text-[var(--primary)]"
                          : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
                      )}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--card)]/80 px-4 backdrop-blur">
          <p className="text-sm text-[var(--muted-foreground)]">Admin</p>
          <UserMenu />
        </header>
        <main className="flex-1 px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  );
}
