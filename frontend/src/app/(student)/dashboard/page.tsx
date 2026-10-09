import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="Home" description="Your academy overview." />
      <EmptyState title="Nothing due right now" description="Enrollments and deadlines appear after admission." />
    </>
  );
}
