"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth/auth-context";
import { isAuthPublicPath, loginRedirectUrl } from "@/lib/auth/session";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (user) return;
    if (isAuthPublicPath(pathname)) return;
    router.replace(loginRedirectUrl(`${pathname}${window.location.search}`));
  }, [loading, user, pathname, router]);

  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-[var(--muted-foreground)]">
        Checking session…
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-[var(--muted-foreground)]">
        Redirecting to sign in…
      </div>
    );
  }

  return <>{children}</>;
}
