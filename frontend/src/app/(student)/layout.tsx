import { RequireAuth } from "@/components/shared/require-auth";
import { StudentShell } from "@/components/shells/student-shell";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <StudentShell>{children}</StudentShell>
    </RequireAuth>
  );
}
