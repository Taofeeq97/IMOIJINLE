"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Award, BookOpen, Calendar, CreditCard, Home, User } from "lucide-react";

import { UserMenu } from "@/components/shared/user-menu";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/learning", label: "Learn", icon: BookOpen },
  { href: "/certificates", label: "Certs", icon: Award },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/payments", label: "Pay", icon: CreditCard },
  { href: "/profile", label: "Me", icon: User },
];

export function StudentShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-dvh bg-[var(--background)]">
      <aside className="hidden w-56 shrink-0 border-r bg-[var(--card)] p-4 lg:block">
        <Link href="/learning" className="font-display text-lg font-semibold">
          Imo Ijinle
        </Link>
        <nav className="mt-8 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm",
                  active
                    ? "bg-[var(--secondary)] font-medium text-[var(--primary)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--card)]/80 px-4 backdrop-blur">
          <p className="text-sm text-[var(--muted-foreground)]">My learning</p>
          <UserMenu />
        </header>
        <main className="flex-1 px-4 py-6 pb-24 lg:pb-6">{children}</main>
        <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t bg-[var(--card)] pb-[env(safe-area-inset-bottom)] lg:hidden">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex min-h-14 flex-1 flex-col items-center justify-center gap-1 text-[10px]",
                  active ? "text-[var(--primary)]" : "text-[var(--muted-foreground)]",
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
