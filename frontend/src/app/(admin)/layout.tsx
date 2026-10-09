import { RequireAuth } from "@/components/shared/require-auth";
import { AdminShell } from "@/components/shells/admin-shell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AdminShell>{children}</AdminShell>
    </RequireAuth>
  );
}
