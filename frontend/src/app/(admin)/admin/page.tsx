"use client";

import Link from "next/link";

import { ResponsiveTable } from "@/components/adaptive/responsive-table";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const demoRows = [
  { id: "1", name: "Foundation Class", status: "Draft" },
  { id: "2", name: "Advanced Class", status: "Published" },
];

export default function AdminHomePage() {
  return (
    <>
      <PageHeader
        title="Overview"
        description="Staff dashboard for cohorts, admissions, subjects, and finance."
        actions={
          <Button asChild>
            <Link href="/admin/cohorts">Manage cohorts</Link>
          </Button>
        }
      />
      <div className="mb-8">
        <EmptyState
          title="No live stats yet"
          description="Cohort and admissions metrics will appear here as data grows."
        />
      </div>
      <ResponsiveTable
        title="Sample table"
        description="Shared table pattern used across admin list pages."
        columns={[
          { id: "name", header: "Class", cell: (r) => r.name, priority: "high" },
          {
            id: "status",
            header: "Status",
            cell: (r) => <Badge className="capitalize">{r.status}</Badge>,
            priority: "medium",
          },
        ]}
        data={demoRows}
        getRowId={(r) => r.id}
      />
    </>
  );
}
