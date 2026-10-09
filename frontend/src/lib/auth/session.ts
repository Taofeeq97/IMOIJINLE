"use client";

type SessionExpiredHandler = (reason?: string) => void;

let onExpired: SessionExpiredHandler | null = null;
let redirecting = false;

export function registerSessionExpiredHandler(handler: SessionExpiredHandler | null) {
  onExpired = handler;
}

export function notifySessionExpired(reason = "Session expired. Please sign in again.") {
  if (redirecting) return;
  redirecting = true;
  try {
    onExpired?.(reason);
  } finally {
    // Allow another redirect later in the same SPA session after login
    window.setTimeout(() => {
      redirecting = false;
    }, 1500);
  }
}

export function isAuthPublicPath(pathname: string) {
  return (
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/forgot") ||
    pathname.startsWith("/reset-password") ||
    pathname.startsWith("/onboarding") ||
    pathname.startsWith("/apply") ||
    pathname.startsWith("/verify") ||
    pathname === "/" ||
    pathname.startsWith("/cohorts") ||
    pathname.startsWith("/programs") ||
    pathname.startsWith("/pages")
  );
}

export function loginRedirectUrl(nextPath?: string) {
  if (typeof window === "undefined") return "/login";
  const next = nextPath ?? `${window.location.pathname}${window.location.search}`;
  if (!next || next.startsWith("/login")) return "/login";
  return `/login?next=${encodeURIComponent(next)}`;
}
