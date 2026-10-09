import Link from "next/link";

import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";

export default function AdminSettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Org configuration" />
      <div className="mb-6">
        <Button asChild>
          <Link href="/admin/settings/payments">Payment configuration</Link>
        </Button>
      </div>
      <EmptyState title="More settings later" description="Terminology, email templates, and branding editors expand in later milestones." />
    </>
  );
}
