import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";

export default function ResetPage() {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <PageHeader title="Reset password" description="Use the link from your email." />
      <EmptyState title="Paste uid + token from email" description="Full reset form wired in M0 auth API." />
    </div>
  );
}
