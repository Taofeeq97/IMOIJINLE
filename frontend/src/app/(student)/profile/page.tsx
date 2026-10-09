"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/auth-context";

export default function ProfilePage() {
  const { user, logout, loading } = useAuth();

  return (
    <>
      <PageHeader title="Profile" description={loading ? "Loading…" : user?.email ?? "Not signed in"} />
      {user ? (
        <div className="space-y-4 rounded-[var(--radius)] border bg-[var(--card)] p-6">
          <p className="text-sm">
            <span className="text-[var(--muted-foreground)]">Name: </span>
            {user.full_name}
          </p>
          <p className="text-sm">
            <span className="text-[var(--muted-foreground)]">Roles: </span>
            {user.roles.map((r) => r.role).join(", ")}
          </p>
          <Button variant="outline" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      ) : null}
    </>
  );
}
