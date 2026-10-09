"use client";

import { RequireAuth } from "@/components/shared/require-auth";

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
