import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";

export default function CalendarPage() {
  return (
    <>
      <PageHeader title="Calendar" />
      <EmptyState title="No upcoming sessions" />
    </>
  );
}
